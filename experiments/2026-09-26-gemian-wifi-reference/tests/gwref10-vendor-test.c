// SPDX-License-Identifier: GPL-2.0
/*
 * Host fixture for the observer's vendor helpers against the pinned gen3
 * declarations: header gating before any read, HIF length bounds with
 * poisoned tails, allow-listed payloads with strict lengths, header-only
 * for everything else, address classes without addresses, descriptor
 * fields, filtered beacons, record length bound with maximal values.
 */
#define GWREF10_HOST_VENDOR
#include "gwref10-host.h"
#include "gwref10-vendor-stub.h"
#include "../lifecycle/gwref10.c"
#include <assert.h>

unsigned long jiffies;
extern const struct kernel_param_ops *gwref10_host_ops;

static char last[512];
static size_t lines;
static char all[65536];

void host_printk(const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	vsnprintf(last, sizeof(last), fmt, ap);
	va_end(ap);
	lines++;
	strncat(all, last, sizeof(all) - strlen(all) - 1);
}

static const UINT_8 AP[6] = { 0x02, 0x11, 0x22, 0x33, 0x44, 0x55 };
static const UINT_8 OWN[6] = { 0x02, 0x66, 0x77, 0x88, 0x99, 0xaa };
static const UINT_8 OTHER[6] = { 0x02, 0xde, 0xad, 0xbe, 0xef, 0x01 };
static const UINT_8 BCAST[6] = { 0xff, 0xff, 0xff, 0xff, 0xff, 0xff };

static BSS_INFO_T bss0;
static ADAPTER_T adapter;

static void arm(void)
{
	memset(&gwref10, 0, sizeof(gwref10));
	pthread_mutex_init(&gwref10.lock, NULL);
	all[0] = 0;
	lines = 0;
	assert(gwref10_host_ops->set("1", NULL) == 0);
}

static int no_address_leak(void)
{
	/* No record may contain the AP, own or other address bytes as hex pairs in sequence. */
	return !strstr(all, "11:22") && !strstr(all, "112233") && !strstr(all, "66:77") && !strstr(all, "667788") &&
	       !strstr(all, "de:ad") && !strstr(all, "deadbe") && !strstr(all, "0x11 0x22") && !strstr(all, "0x02, 0x11");
}

/* The buffer is exactly the delivered byte count (or the header when fewer were delivered), so a read
 * beyond the delivered bytes is an out-of-bounds access the sanitizer reports. */
static void event(UINT_8 eid, UINT_8 seq, const void *body, UINT_16 body_len, UINT_16 declared, UINT_16 hif)
{
	size_t alloc = hif > 8 ? hif : 8;
	UINT_8 *buf = malloc(alloc);
	WIFI_EVENT_T *e = (WIFI_EVENT_T *) buf;
	SW_RFB_T rfb = { .pucRecvBuff = buf };

	assert(buf);
	memset(buf, 0xff, alloc);
	e->u2PacketLength = declared;
	e->u2PacketType = 0xe000;
	e->ucEID = eid;
	e->ucSeqNum = seq;
	e->aucReserved[0] = e->aucReserved[1] = 0;
	memcpy(e->aucBuffer, body, body_len < alloc - 8 ? body_len : alloc - 8);
	gwref10_rx_ingress(&rfb, hif);
	gwref10_event(&adapter, &rfb);
	free(buf);
}

int main(void)
{
	memcpy(bss0.aucBSSID, AP, 6);
	memcpy(bss0.aucOwnMacAddr, OWN, 6);
	adapter.aprBssInfo[0] = &bss0;

	/* --- commands --- */
	arm();
	{
		CMD_INFO_T info = { .eCmdType = COMMAND_TYPE_NETWORK_IOCTL, .u2InfoBufLen = 4, .pucInfoBuffer = NULL, .ucBssIndex = 0 };

		gwref10_cmd(&adapter, &info);	/* NULL buffer: nothing dereferenced */
		assert(!strcmp(last, "<7>gwref10 cmd: n=1 type=1 short=1 len=4 bss=0\n"));
		UINT_8 tiny[4] = { 0xff, 0xff, 0xff, 0xff };
		info.pucInfoBuffer = tiny;
		gwref10_cmd(&adapter, &info);	/* shorter than the header: header not read */
		assert(!strcmp(last, "<7>gwref10 cmd: n=2 type=1 short=1 len=4 bss=0\n"));
		info.eCmdType = COMMAND_TYPE_SECURITY_FRAME;
		info.ucStaRecIndex = 3;
		gwref10_cmd(&adapter, &info);
		assert(!strcmp(last, "<7>gwref10 cmd: n=3 type=2 frame=1 len=4 bss=0 sta=3\n"));
	}
	{
		UINT_8 buf[sizeof(WIFI_CMD_T) + sizeof(CMD_802_11_KEY)];
		WIFI_CMD_T *c = (WIFI_CMD_T *) buf;
		CMD_802_11_KEY *k = (CMD_802_11_KEY *) c->aucBuffer;
		CMD_INFO_T info = { .eCmdType = COMMAND_TYPE_NETWORK_IOCTL, .u2InfoBufLen = sizeof(buf), .pucInfoBuffer = buf };

		memset(buf, 0, sizeof(buf));
		c->ucCID = CMD_ID_ADD_REMOVE_KEY;
		c->ucSeqNum = 10;
		c->ucSetQuery = 1;
		k->ucAddRemove = 1; k->ucTxKey = 1; k->ucKeyType = 1; k->ucIsAuthenticator = 0; k->ucBssIdx = 0;
		k->ucAlgorithmId = 4; k->ucKeyId = 0; k->ucKeyLen = 16; k->ucWlanIndex = 1;
		memcpy(k->aucPeerAddr, AP, 6);
		memset(k->aucKeyMaterial, 0x5a, sizeof(k->aucKeyMaterial));
		memset(k->aucKeyRsc, 0xa5, sizeof(k->aucKeyRsc));
		lines = 0;
		gwref10_cmd(&adapter, &info);
		assert(lines == 2);
		assert(!strcmp(last, "<7>gwref10 cmd: n=5 key seq=10 addremove=1 tx=1 keytype=1 auth=0 bss=0 alg=4 keyid=0 keylen=16 wlan=1 peer=bss\n"));
		/* The key material (0x5a) and RSC (0xa5) are never formatted: the record text is exact above,
		 * and no run of their byte patterns appears anywhere in the output. */
		assert(!strstr(all, "5a5a") && !strstr(all, "a5a5") && !strstr(all, "9090") && !strstr(all, "165165"));
		/* group key to the broadcast peer; own, zero and other classes */
		memcpy(k->aucPeerAddr, BCAST, 6); k->ucKeyType = 0; k->ucKeyId = 1;
		gwref10_cmd(&adapter, &info);
		assert(strstr(last, " keytype=0 ") && strstr(last, " keyid=1 ") && strstr(last, "peer=bcast\n"));
		memcpy(k->aucPeerAddr, OWN, 6); gwref10_cmd(&adapter, &info); assert(strstr(last, "peer=own\n"));
		memset(k->aucPeerAddr, 0, 6); gwref10_cmd(&adapter, &info); assert(strstr(last, "peer=zero\n"));
		memcpy(k->aucPeerAddr, OTHER, 6); gwref10_cmd(&adapter, &info); assert(strstr(last, "peer=other\n"));
		k->aucPeerAddr[0] = 0x01; gwref10_cmd(&adapter, &info); assert(strstr(last, "peer=group\n"));
		/* a removal just long enough for the metadata, and one byte short of it */
		info.u2InfoBufLen = sizeof(WIFI_CMD_T) + OFFSET_OF(CMD_802_11_KEY, aucKeyMaterial);
		k->ucAddRemove = 0;
		lines = 0; gwref10_cmd(&adapter, &info); assert(lines == 2 && strstr(last, " addremove=0 "));
		info.u2InfoBufLen--;
		lines = 0; gwref10_cmd(&adapter, &info); assert(lines == 1 && strstr(last, "cid=0x07 "));
		/* BSS index out of range never dereferences the table */
		info.u2InfoBufLen = sizeof(buf); k->ucBssIdx = 7; memcpy(k->aucPeerAddr, AP, 6);
		gwref10_cmd(&adapter, &info); assert(strstr(last, " bss=7 ") && strstr(last, "peer=other\n"));
	}
	{
		UINT_8 buf[sizeof(WIFI_CMD_T) + sizeof(CMD_SET_BSS_INFO)];
		WIFI_CMD_T *c = (WIFI_CMD_T *) buf;
		CMD_SET_BSS_INFO *b = (CMD_SET_BSS_INFO *) c->aucBuffer;
		CMD_INFO_T info = { .eCmdType = COMMAND_TYPE_NETWORK_IOCTL, .u2InfoBufLen = sizeof(buf), .pucInfoBuffer = buf };

		memset(buf, 0, sizeof(buf));
		c->ucCID = CMD_ID_SET_BSS_INFO; c->ucSeqNum = 11;
		b->ucBssIndex = 0; b->ucConnectionState = 1; b->ucAuthMode = 6; b->ucEncStatus = 2; b->ucBMCWlanIndex = 0;
		memcpy(b->aucBSSID, AP, 6);
		memset(b->aucSSID, 'N', sizeof(b->aucSSID)); b->ucSSIDLen = 8;
		lines = 0; gwref10_cmd(&adapter, &info);
		assert(lines == 2 && strstr(last, " bssinfo seq=11 bss=0 connstate=1 opmode=0 qbss=0 staofap=0 authmode=6 encstatus=2 physet=0 bmcwlan=0\n"));
		assert(!strstr(all, "NNNN"));
		/* unknown command id: header only */
		c->ucCID = 0x7e; lines = 0; gwref10_cmd(&adapter, &info); assert(lines == 1);
	}
	assert(no_address_leak());

	/* --- events --- */
	arm();
	{
		EVENT_ADD_KEY_DONE_INFO done = { .ucBSSIndex = 0 };

		memcpy(done.aucStaAddr, AP, 6);
		lines = 0;
		event(EVENT_ID_ADD_PKEY_DONE, 0, &done, sizeof(done), 16, 20);
		assert(lines == 2 && !strcmp(last, "<7>gwref10 event: n=2 keydone seq=0 bss=0 sta=bss\n"));
		/* HIF delivered less than the header: nothing read */
		lines = 0; event(EVENT_ID_ADD_PKEY_DONE, 0, &done, sizeof(done), 16, 6);
		assert(lines == 1 && !strcmp(last, "<7>gwref10 event: n=3 shorthdr=1 hif=6\n"));
		/* declared longer than delivered: header then badlen, no payload from the poisoned tail */
		lines = 0; event(EVENT_ID_ADD_PKEY_DONE, 0, &done, sizeof(done), 16, 12);
		assert(lines == 2 && !strcmp(last, "<7>gwref10 event: n=5 eid=0x24 seq=0 badlen=1\n"));
		/* declared shorter than the struct: header only */
		lines = 0; event(EVENT_ID_ADD_PKEY_DONE, 0, &done, sizeof(done), 15, 20);
		assert(lines == 1 && strstr(last, "eid=0x24 seq=0 len=15 hif=20\n"));
		/* declared below the header or above the buffer */
		lines = 0; event(EVENT_ID_ADD_PKEY_DONE, 0, &done, sizeof(done), 4, 20);
		assert(lines == 2 && strstr(last, "badlen=1\n"));
		lines = 0; event(EVENT_ID_ADD_PKEY_DONE, 0, &done, sizeof(done), CFG_RX_MAX_PKT_SIZE + 1, CFG_RX_MAX_PKT_SIZE + 1);
		assert(lines == 2 && strstr(last, "badlen=1\n"));
		/* other station classes */
		memcpy(done.aucStaAddr, OTHER, 6); event(EVENT_ID_ADD_PKEY_DONE, 0, &done, sizeof(done), 16, 16);
		assert(strstr(last, "sta=other\n"));
	}
	{
		/* the link-quality response stays header-only in the active configuration */
		UINT_8 lq[24]; memset(lq, 0x11, sizeof(lq));
		lines = 0; event(EVENT_ID_LINK_QUALITY, 9, lq, sizeof(lq), 8 + sizeof(lq), 8 + sizeof(lq));
		assert(lines == 1 && strstr(last, " eid=0x02 seq=9 len=32 hif=32\n"));
	}
	{
		EVENT_TX_DONE_T td = { .ucPacketSeq = 3, .ucStatus = 0, .u2SequenceNumber = 77, .ucWlanIndex = 1, .ucTxCount = 1, .u2TxRate = 0x2c, .ucFlag = 0 };

		lines = 0; event(EVENT_ID_TX_DONE, 0, &td, sizeof(td), 8 + sizeof(td), 8 + sizeof(td));
		assert(lines == 2 && strstr(last, " txdone seq=0 pid=3 status=0 sn=77 wlan=1 count=1 rate=44 flag=0\n"));
	}
	{
		/* queue-management events carry the header inside their struct */
		EVENT_BSS_ABSENCE_PRESENCE_T ab = { .ucBssIndex = 0, .ucIsAbsent = 1, .ucBssFreeQuota = 5 };
		UINT_8 *body = ((UINT_8 *) &ab) + 8;

		lines = 0; event(EVENT_ID_BSS_ABSENCE_PRESENCE, 2, body, sizeof(ab) - 8, sizeof(ab), sizeof(ab));
		assert(lines == 2 && strstr(last, " absence seq=2 bss=0 absent=1 quota=5\n"));
		lines = 0; event(EVENT_ID_BSS_ABSENCE_PRESENCE, 2, body, sizeof(ab) - 8, sizeof(ab) - 1, sizeof(ab) - 1);
		assert(lines == 1);
	}
	{
		EVENT_RX_ADDBA_T ba = { .ucStaRecIdx = 0, .ucDialogToken = 9, .u2BAParameterSet = 0x1002, .u2BATimeoutValue = 0, .u2BAStartSeqCtrl = 0x0150 };

		lines = 0; event(EVENT_ID_RX_ADDBA, 1, ((UINT_8 *) &ba) + 8, sizeof(ba) - 8, sizeof(ba), sizeof(ba));
		assert(lines == 2 && strstr(last, " addba seq=1 sta=0 token=9 param=0x1002 timeout=0 ssn=0x0150\n"));
	}
	{
		/* header-only ids: unknown, debug, and the BA drop-SN event without a pinned struct */
		UINT_8 junk[40]; memset(junk, 0x7f, sizeof(junk));
		lines = 0; event(0x27, 0, junk, sizeof(junk), 48, 48); assert(lines == 1);
		lines = 0; event(0x51, 0, junk, sizeof(junk), 48, 48); assert(lines == 1);
		lines = 0; event(0x7f, 5, junk, sizeof(junk), 48, 48); assert(lines == 1 && strstr(last, "eid=0x7f seq=5 len=48 hif=48\n"));
	}
	assert(no_address_leak());

	/* --- credits --- */
	arm();
	{
		UINT_16 rel[TC_NUM] = { 0 };
		TX_TCQ_STATUS_T tcq = { .au2FreePageCount = { 5, 5, 5, 5, 2, 0 } };

		lines = 0; gwref10_credit(rel, &tcq); assert(lines == 0);
		rel[TC4_INDEX] = 1;
		gwref10_credit(rel, &tcq);
		assert(!strcmp(last, "<7>gwref10 credit: n=1 rel0=0 rel1=0 rel2=0 rel3=0 rel4=1 rel5=0 free0=5 free1=5 free2=5 free3=5 free4=2 free5=0\n"));
	}

	/* --- receive descriptors --- */
	arm();
	{
		/* Each case allocates exactly the delivered bytes; pvHeader is placed as the driver would. */
		UINT_8 *buf;
		HW_MAC_RX_DESC_T *d;
		SW_RFB_T rfb;
#define RX_CASE(hifbytes) do { buf = malloc(hifbytes); assert(buf); memset(buf, 0xff, hifbytes); d = (HW_MAC_RX_DESC_T *) buf; \
		memset(buf, 0, (hifbytes) < sizeof(*d) ? (hifbytes) : sizeof(*d)); rfb.pucRecvBuff = buf; rfb.prRxStatus = d; \
		rfb.pvHeader = buf + sizeof(*d); gwref10_rx_ingress(&rfb, hifbytes); } while (0)
#define RX_DONE() free(buf)

		/* protected QoS data from the AP to us, untranslated, 24-byte header, 120 bytes after the descriptor */
		RX_CASE(136);
		d->u2RxByteCount = 136; d->u2PktTYpe = 0x4000; d->ucMatchPacket = RX_STATUS_UC2ME;
		d->ucHeaderLen = 26; d->ucBssid = 1 << 2; d->ucWlanIdx = 1; d->ucTidSecMode = 4 << 4; d->u2StatusFlag = 0;
		{ UINT_8 *hdr = buf + 16; hdr[0] = 0x88; hdr[1] = 0x41; memcpy(hdr + 4, OWN, 6); memcpy(hdr + 10, AP, 6); }
		rfb.u2PacketLen = 120;
		lines = 0; gwref10_rxd(&rfb);
		assert(lines == 1 && !strcmp(last, "<7>gwref10 rxd: n=1 type=2 len=120 span=120 off=16 hdrlen=26 pad=0 trans=0 bssid=1 wlan=1 tid=0 sec=4 status=0x0000 mismatch=0 fmt=0 uc2me=1 mc=0 bc=0 grp=0 fc=0x4188 havefc=1 eth=0x0000\n"));
		/* a beacon and a probe response are filtered, not recorded */
		{ UINT_8 *hdr = buf + 16; hdr[0] = 0x80; hdr[1] = 0x00; memcpy(hdr + 4, BCAST, 6); d->ucMatchPacket = RX_STATUS_BC_FRAME; }
		lines = 0; gwref10_rxd(&rfb); assert(lines == 0 && gwref10.filtered[GWREF10_RXD] == 1);
		buf[16] = 0x50; lines = 0; gwref10_rxd(&rfb); assert(lines == 0 && gwref10.filtered[GWREF10_RXD] == 2);
		RX_DONE();

		/* translated broadcast ARP: group bit from the match flags, Ethernet type from the 14-byte header */
		RX_CASE(76);
		d->u2RxByteCount = 76; d->u2PktTYpe = 0x4000; d->ucHeaderLen = 14 | RX_STATUS_HEADER_TRAN; d->ucMatchPacket = RX_STATUS_BC_FRAME;
		d->ucBssid = 1 << 2; d->ucTidSecMode = 4 << 4;
		{ UINT_8 *hdr = buf + 16; memcpy(hdr, BCAST, 6); memcpy(hdr + 6, AP, 6); hdr[12] = 0x08; hdr[13] = 0x06; }
		rfb.u2PacketLen = 60;
		lines = 0; gwref10_rxd(&rfb);
		assert(lines == 1 && strstr(last, " span=60 off=16 ") && strstr(last, " trans=1 ") && strstr(last, " bc=1 grp=1 fc=0x0000 havefc=0 eth=0x0806\n"));
		RX_DONE();

		/* the descriptor's count beyond the delivered bytes is refused before any header read */
		RX_CASE(40);
		d->u2RxByteCount = 76; rfb.u2PacketLen = 60;
		lines = 0; gwref10_rxd(&rfb); assert(lines == 1 && !strcmp(last, "<7>gwref10 rxd: n=3 badlen=1 declared=76 hif=40\n"));
		RX_DONE();
		/* fewer delivered bytes than the descriptor */
		RX_CASE(8);
		lines = 0; gwref10_rxd(&rfb); assert(lines == 1 && !strcmp(last, "<7>gwref10 rxd: n=4 shortdesc=1 hif=8\n"));
		RX_DONE();
		/* a declared count below the descriptor size (the driver's u2PacketLen would have wrapped) */
		RX_CASE(40);
		d->u2RxByteCount = 12; rfb.u2PacketLen = 0xfff0;
		lines = 0; gwref10_rxd(&rfb); assert(lines == 1 && !strcmp(last, "<7>gwref10 rxd: n=5 badlen=1 declared=12 hif=40\n"));
		RX_DONE();
		/* a header pointer beyond the declared end (status groups and padding larger than declared) */
		RX_CASE(64);
		d->u2RxByteCount = 40; rfb.pvHeader = buf + 48; rfb.u2PacketLen = 0xfff8;
		lines = 0; gwref10_rxd(&rfb); assert(lines == 1 && !strcmp(last, "<7>gwref10 rxd: n=6 badhdr=1 declared=40 hif=64\n"));
		rfb.pvHeader = buf + 8;	/* inside the descriptor */
		lines = 0; gwref10_rxd(&rfb); assert(lines == 1 && strstr(last, " badhdr=1 "));
		RX_DONE();
		/* a wrapped u2PacketLen with a valid short span: no header bytes are read beyond the span */
		RX_CASE(36);
		d->u2RxByteCount = 36; rfb.pvHeader = buf + 20; rfb.u2PacketLen = 0xfff0; d->ucHeaderLen = 24;
		lines = 0; gwref10_rxd(&rfb);
		assert(lines == 1 && strstr(last, " len=65520 span=16 off=20 ") && strstr(last, " havefc=0 eth=0x0000\n"));
		RX_DONE();
		/* short native and translated spans: 23 and 13 bytes read nothing from the frame */
		RX_CASE(39);
		d->u2RxByteCount = 39; rfb.u2PacketLen = 23;
		lines = 0; gwref10_rxd(&rfb); assert(lines == 1 && strstr(last, " span=23 ") && strstr(last, " havefc=0 "));
		RX_DONE();
		RX_CASE(29);
		d->u2RxByteCount = 29; d->ucHeaderLen = 14 | RX_STATUS_HEADER_TRAN; rfb.u2PacketLen = 13;
		lines = 0; gwref10_rxd(&rfb); assert(lines == 1 && strstr(last, " span=13 ") && strstr(last, " eth=0x0000\n"));
		RX_DONE();
		/* every field at its maximum stays under the line bound without truncation */
		RX_CASE(CFG_RX_MAX_PKT_SIZE);
		d->u2RxByteCount = CFG_RX_MAX_PKT_SIZE; d->u2PktTYpe = 0xffff; d->ucMatchPacket = 0xff; d->ucHeaderLen = 0x7f; d->ucBssid = 0xff;
		d->ucWlanIdx = 0xff; d->ucTidSecMode = 0xff; d->u2StatusFlag = 0xffff; rfb.u2PacketLen = 0xffff; rfb.pvHeader = buf + 16;
		buf[16] = 0xff; buf[17] = 0xff; buf[20] = 0xff;
		lines = 0; gwref10_rxd(&rfb);
		assert(lines == 1 && !strstr(last, "trunc=1") && strlen(last) < GWREF10_LINE && gwref10.truncated == 0);
		RX_DONE();
		/* and a declared count above the buffer size is refused */
		RX_CASE(CFG_RX_MAX_PKT_SIZE + 4);
		d->u2RxByteCount = CFG_RX_MAX_PKT_SIZE + 4; rfb.u2PacketLen = 100;
		lines = 0; gwref10_rxd(&rfb); assert(lines == 1 && strstr(last, " badlen=1 "));
		RX_DONE();
#undef RX_CASE
#undef RX_DONE
	}
	assert(no_address_leak());

	/* --- transmit descriptors --- */
	arm();
	{
		HW_MAC_TX_DESC_T td; MSDU_INFO_T m = { .ucPacketType = 0, .ucStaRecIndex = 0, .ucBssIndex = 0, .ucWlanIndex = 1,
						    .fgIs802_1x = 0, .fgIs802_11 = 0, .u2FrameLength = 98, .ucPID = 3, .ucTC = 1 };

		memset(&td, 0, sizeof(td));
		td.ucHeaderPadding = TX_DESC_PROTECTED_FRAME | (0 << TX_DESC_TID_OFFSET);
		gwref10_txd(&m, &td, 0);
		assert(!strcmp(last, "<7>gwref10 txd: n=1 cls=data pid=3 wlan=1 bss=0 sta=0 len=98 fmt=0 tid=0 prot=1 is80211=0 tc=1\n"));
		m.fgIs802_1x = 1; td.ucHeaderPadding = 0; gwref10_txd(&m, &td, 1);
		assert(strstr(last, "cls=eapol ") && strstr(last, " prot=0 "));
		m.fgIs802_1x = 0; m.ucPacketType = TX_PACKET_TYPE_MGMT; m.fgIs802_11 = 1;
		td.ucHeaderFormat = 2 << TX_DESC_HEADER_FORMAT_OFFSET; gwref10_txd(&m, &td, 0);
		assert(strstr(last, "cls=mgmt ") && strstr(last, " fmt=2 ") && strstr(last, " is80211=1 "));
	}

	/* --- state --- */
	{
		STA_RECORD_T sta = { .ucIndex = 0, .ucWlanIndex = 1, .ucBssIndex = 0, .ucStaState = 3 };

		gwref10_sta_state(&sta, 1); assert(strstr(last, " stastate sta=0 wlan=1 bss=0 from=3 to=1\n"));
		gwref10_sta_free(&sta); assert(strstr(last, " stafree sta=0 wlan=1 bss=0 state=3\n"));
		gwref10_bss_deactivate(0); assert(strstr(last, " bssdeact bss=0\n"));
	}
	assert(no_address_leak());

	/* --- idle: no helper records anything --- */
	assert(gwref10_host_ops->set("2", NULL) == 0);
	lines = 0;
	{
		STA_RECORD_T sta = { 0 };
		gwref10_sta_free(&sta); gwref10_bss_deactivate(0);
	}
	assert(lines == 0);
	puts("gwref10-vendor-test: helpers gated, bounded and sanitized against the pinned declarations; no device");
	return 0;
}
