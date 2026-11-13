// ==UserScript==
// @name        Gemini: prefer codecs the MT6797 decodes
// @description Report AV1 and 10-bit VP9 as unsupported so sites send VP9 profile 0 or H.264, which the hardware decoder handles.
// @match       *://*/*
// @run-at      document-start
// @grant       none
// ==/UserScript==
// SPDX-License-Identifier: MIT
// The MT6797 decoder (mt6797-vdec, through libva-v4l2-request-mt6797) handles H.264, HEVC and
// 8-bit VP9; AV1 and 10-bit VP9 would decode in software, at about three times the CPU.
(function () {
  'use strict';
  const blocked = (t) => /av01|av1|vp09\.0[123]/i.test(String(t || ''));
  const ms = window.MediaSource;
  if (ms && ms.isTypeSupported) {
    const orig = ms.isTypeSupported.bind(ms);
    ms.isTypeSupported = (t) => !blocked(t) && orig(t);
  }
  const cpt = HTMLMediaElement.prototype.canPlayType;
  HTMLMediaElement.prototype.canPlayType = function (t) { return blocked(t) ? '' : cpt.call(this, t); };
  const mc = navigator.mediaCapabilities;
  if (mc && mc.decodingInfo) {
    const orig = mc.decodingInfo.bind(mc);
    mc.decodingInfo = (cfg) => {
      const ct = cfg && cfg.video && cfg.video.contentType;
      return blocked(ct) ? Promise.resolve({ supported: false, smooth: false, powerEfficient: false })
                         : orig(cfg);
    };
  }
})();
