// SPDX-License-Identifier: MIT
/*
 * Show a libcamera camera on the panel, with its software ISP doing colour and
 * exposure. Nothing is saved. The panel scans 1080x2160, turned 90 degrees when
 * held in landscape.
 *
 * usage: cam-fb [FRAMES [WIDTH HEIGHT [plain]]]
 *   plain: ask for no mirror. By default this asks for a mirrored picture, as the
 *   owner chose, since libcamera sets the sensor's flip itself.
 */
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <map>
#include <memory>
#include <semaphore.h>
#include <time.h>
#include <sys/mman.h>
#include <unistd.h>
#include <vector>

#include <libcamera/libcamera.h>

using namespace libcamera;

static constexpr unsigned int FB_W = 1080, FB_H = 2160;

static sem_t done;
static std::vector<Request *> finished;
static unsigned int completed;

static void requestComplete(Request *request)
{
	finished.push_back(request);
	sem_post(&done);
}

int main(int argc, char **argv)
{
	unsigned int frames = argc > 1 ? atoi(argv[1]) : 60;
	unsigned int width = argc > 3 ? atoi(argv[2]) : 1280;
	unsigned int height = argc > 3 ? atoi(argv[3]) : 960;
	bool plain = argc > 4 && !strcmp(argv[4], "plain");

	sem_init(&done, 0, 0);

	CameraManager cm;
	if (cm.start()) {
		std::cerr << "camera manager failed" << std::endl;
		return 1;
	}
	if (cm.cameras().empty()) {
		std::cerr << "no cameras" << std::endl;
		return 1;
	}
	std::shared_ptr<Camera> camera = cm.cameras()[0];
	std::cout << "camera " << camera->id() << std::endl;
	if (camera->acquire())
		return 1;

	std::unique_ptr<CameraConfiguration> config =
		camera->generateConfiguration({ StreamRole::Viewfinder });
	StreamConfiguration &sc = config->at(0);
	sc.pixelFormat = formats::XRGB8888;
	sc.size = Size(width, height);
	sc.bufferCount = 4;
	if (!plain)
		config->orientation = Orientation::Rotate0Mirror;
	CameraConfiguration::Status status = config->validate();
	std::cout << "config " << (status == CameraConfiguration::Invalid ? "invalid" :
				   status == CameraConfiguration::Adjusted ? "adjusted" : "valid")
		  << " " << sc.toString() << " stride " << sc.stride << " orientation "
		  << config->orientation << std::endl;
	if (status == CameraConfiguration::Invalid || camera->configure(config.get()))
		return 1;
	if (sc.pixelFormat != formats::XRGB8888) {
		std::cerr << "not XRGB8888" << std::endl;
		return 1;
	}

	int fbfd = open("/dev/fb0", O_RDWR);
	if (fbfd < 0)
		return 1;
	auto *fb = static_cast<uint8_t *>(mmap(nullptr, FB_W * 4 * FB_H, PROT_READ | PROT_WRITE,
					       MAP_SHARED, fbfd, 0));
	if (fb == MAP_FAILED)
		return 1;

	FrameBufferAllocator allocator(camera);
	Stream *stream = sc.stream();
	if (allocator.allocate(stream) < 0)
		return 1;

	std::vector<std::unique_ptr<Request>> requests;
	std::map<const FrameBuffer *, const uint8_t *> maps;
	for (const std::unique_ptr<FrameBuffer> &buffer : allocator.buffers(stream)) {
		std::unique_ptr<Request> request = camera->createRequest();
		const FrameBuffer::Plane &plane = buffer->planes()[0];
		void *m = mmap(nullptr, plane.offset + plane.length, PROT_READ, MAP_SHARED,
			       plane.fd.get(), 0);

		if (m == MAP_FAILED || request->addBuffer(stream, buffer.get()))
			return 1;
		maps[buffer.get()] = static_cast<const uint8_t *>(m) + plane.offset;
		requests.push_back(std::move(request));
	}

	camera->requestCompleted.connect(requestComplete);
	if (camera->start())
		return 1;
	for (std::unique_ptr<Request> &request : requests)
		camera->queueRequest(request.get());

	/* The panel's scan runs along the picture's width, turned as the console is. */
	unsigned int u0 = (FB_H - std::min(sc.size.width, FB_H)) / 2;
	unsigned int v0 = (FB_W - std::min(sc.size.height, FB_W)) / 2;

	while (completed < frames) {
		timespec ts;

		clock_gettime(CLOCK_REALTIME, &ts);
		ts.tv_sec += 3;
		if (sem_timedwait(&done, &ts)) {
			std::cerr << "timed out at frame " << completed << std::endl;
			break;
		}
		Request *request = finished.front();
		finished.erase(finished.begin());
		completed++;

		if (request->status() == Request::RequestComplete) {
			const FrameBuffer *buffer = request->buffers().begin()->second;
			const uint8_t *src = maps[buffer];

			for (unsigned int y = 0; y < std::min(sc.size.height, FB_W); y++) {
				const uint32_t *line =
					reinterpret_cast<const uint32_t *>(src + y * sc.stride);

				for (unsigned int x = 0; x < std::min(sc.size.width, FB_H); x++)
					*(reinterpret_cast<uint32_t *>(
						  fb + (FB_H - 1 - (u0 + x)) * FB_W * 4) +
					  v0 + y) = line[x];
			}
			if (completed % 15 == 0) {
				const ControlList &m = request->metadata();
				auto e = m.get(controls::ExposureTime);
				auto g = m.get(controls::AnalogueGain);
				auto c = m.get(controls::ColourGains);

				std::cout << "frame " << completed << " exposure "
					  << (e ? *e : -1) << " gain " << (g ? *g : -1.f)
					  << " colour gains " << (c ? (*c)[0] : -1.f) << " "
					  << (c ? (*c)[1] : -1.f) << std::endl;
			}
		}
		request->reuse(Request::ReuseBuffers);
		camera->queueRequest(request);
	}

	camera->stop();
	allocator.free(stream);
	camera->release();
	camera.reset();
	cm.stop();
	std::cout << "frames " << completed << " of " << frames << std::endl;
	return completed == frames ? 0 : 1;
}
