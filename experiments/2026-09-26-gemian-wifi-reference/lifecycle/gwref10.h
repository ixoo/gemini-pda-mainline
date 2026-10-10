/* SPDX-License-Identifier: GPL-2.0 */
/*
 * gemini-wifi-ref-v10: bounded firmware-boundary lifecycle observer.
 *
 * Records index, flag, length, status and class fields of the gen3 driver's
 * commands, firmware events, page credits, receive and transmit descriptors
 * and station/BSS teardown while armed. Never formats an address, an SSID, a
 * key byte, a receive sequence counter or a frame body. Single shared state,
 * explicit arm and seal through one module parameter, finite caps and an
 * internal monotonic deadline. High-volume records are KERN_DEBUG so they
 * enter the kernel log without reaching the consoles at loglevel 7; only
 * arm, seal and cap markers are KERN_INFO. Receive payload fields are read
 * only within the byte count the HIF actually delivered for that buffer,
 * which the ingress paths store in the buffer (u2GwrefHifLen).
 */
#ifndef _GWREF10_H
#define _GWREF10_H

enum gwref10_category {
	GWREF10_CMD,
	GWREF10_EVENT,
	GWREF10_CREDIT,
	GWREF10_RXD,
	GWREF10_TXD,
	GWREF10_STATE,
	GWREF10_CATEGORIES
};

enum gwref10_class {
	GWREF10_PEER_BSS,	/* equals the BSS's target address */
	GWREF10_PEER_OWN,	/* equals the BSS's own address */
	GWREF10_PEER_BCAST,	/* ff:ff:ff:ff:ff:ff */
	GWREF10_PEER_ZERO,	/* 00:00:00:00:00:00 */
	GWREF10_PEER_GROUP,	/* another group address */
	GWREF10_PEER_OTHER	/* another unicast address */
};

/* Core (no vendor types; host-testable). */
int gwref10_armed(void);
void gwref10_record(enum gwref10_category category, const char *fmt, ...);
void gwref10_filtered(enum gwref10_category category);

#ifndef GWREF10_HOST_CORE
struct _ADAPTER_T;
struct _CMD_INFO_T;
struct _SW_RFB_T;
struct _MSDU_INFO_T;
struct _HW_MAC_TX_DESC_T;
struct _STA_RECORD_T;
struct _TX_TCQ_STATUS_T;

void gwref10_cmd(struct _ADAPTER_T *prAdapter, struct _CMD_INFO_T *prCmdInfo);
void gwref10_event(struct _ADAPTER_T *prAdapter, struct _SW_RFB_T *prSwRfb);
void gwref10_credit(const unsigned short *released, const struct _TX_TCQ_STATUS_T *tcq);
void gwref10_rx_ingress(struct _SW_RFB_T *prSwRfb, unsigned int hif_bytes);
void gwref10_rxd(struct _SW_RFB_T *prSwRfb);
void gwref10_txd(struct _MSDU_INFO_T *prMsduInfo, struct _HW_MAC_TX_DESC_T *prTxDesc, int security);
void gwref10_sta_state(const struct _STA_RECORD_T *prStaRec, unsigned int new_state);
void gwref10_sta_free(const struct _STA_RECORD_T *prStaRec);
void gwref10_bss_deactivate(unsigned int bss_index);
#endif

#endif /* _GWREF10_H */
