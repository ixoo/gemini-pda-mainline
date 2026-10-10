/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Minimal stand-ins for the driver objects the observer helpers dereference.
 * Only the fields the helpers name exist here; run-gwref10-vendor-test.py
 * audits each of them against the pinned declarations before compiling.
 * The declarations the helpers need verbatim (commands, events, descriptors)
 * come from the generated header.
 */
#ifndef GWREF10_VENDOR_STUB_H
#define GWREF10_VENDOR_STUB_H
#include "gwref10-vendor-gen.h"

typedef struct _BSS_INFO_T {
	UINT_8 aucBSSID[MAC_ADDR_LEN];
	UINT_8 aucOwnMacAddr[MAC_ADDR_LEN];
} BSS_INFO_T, *P_BSS_INFO_T;

typedef struct _ADAPTER_T {
	P_BSS_INFO_T aprBssInfo[HW_BSSID_NUM + 1];
} ADAPTER_T, *P_ADAPTER_T;

typedef struct _CMD_INFO_T {
	COMMAND_TYPE eCmdType;
	UINT_16 u2InfoBufLen;
	PUINT_8 pucInfoBuffer;
	UINT_8 ucBssIndex;
	UINT_8 ucStaRecIndex;
} CMD_INFO_T, *P_CMD_INFO_T;

typedef struct _SW_RFB_T {
	PUINT_8 pucRecvBuff;
	HW_MAC_RX_DESC_T *prRxStatus;
	PVOID pvHeader;
	UINT_16 u2PacketLen;
	UINT_16 u2GwrefHifLen;
} SW_RFB_T, *P_SW_RFB_T;

typedef struct _MSDU_INFO_T {
	UINT_8 ucPacketType;
	UINT_8 ucStaRecIndex;
	UINT_8 ucBssIndex;
	UINT_8 ucWlanIndex;
	BOOLEAN fgIs802_1x;
	BOOLEAN fgIs802_11;
	UINT_16 u2FrameLength;
	UINT_8 ucPID;
	UINT_8 ucTC;
} MSDU_INFO_T, *P_MSDU_INFO_T;

typedef struct _STA_RECORD_T {
	UINT_8 ucIndex;
	UINT_8 ucWlanIndex;
	UINT_8 ucBssIndex;
	UINT_8 ucStaState;
} STA_RECORD_T, *P_STA_RECORD_T;

typedef HW_MAC_RX_DESC_T *P_HW_MAC_RX_DESC_T;
typedef HW_MAC_TX_DESC_T *P_HW_MAC_TX_DESC_T;
typedef TX_TCQ_STATUS_T *P_TX_TCQ_STATUS_T;
typedef WIFI_CMD_T *P_WIFI_CMD_T;
typedef WIFI_EVENT_T *P_WIFI_EVENT_T;
typedef CMD_802_11_KEY *P_CMD_802_11_KEY;
typedef CMD_BSS_ACTIVATE_CTRL *P_CMD_BSS_ACTIVATE_CTRL;
typedef CMD_UPDATE_STA_RECORD_T *P_CMD_UPDATE_STA_RECORD_T;
typedef CMD_REMOVE_STA_RECORD_T *P_CMD_REMOVE_STA_RECORD_T;
typedef CMD_SET_BSS_INFO *P_CMD_SET_BSS_INFO;
typedef EVENT_ADD_KEY_DONE_INFO *P_EVENT_ADD_KEY_DONE_INFO;
typedef EVENT_TX_DONE_T *P_EVENT_TX_DONE_T;
typedef EVENT_ACTIVATE_STA_REC_T *P_EVENT_ACTIVATE_STA_REC_T;
typedef EVENT_LINK_QUALITY_EX *P_EVENT_LINK_QUALITY_EX;
typedef EVENT_SCAN_DONE *P_EVENT_SCAN_DONE;
typedef EVENT_CH_PRIVILEGE_T *P_EVENT_CH_PRIVILEGE_T;
typedef EVENT_BSS_BEACON_TIMEOUT_T *P_EVENT_BSS_BEACON_TIMEOUT_T;
typedef EVENT_STA_AGING_TIMEOUT_T *P_EVENT_STA_AGING_TIMEOUT_T;
typedef EVENT_RX_ADDBA_T *P_EVENT_RX_ADDBA_T;
typedef EVENT_RX_DELBA_T *P_EVENT_RX_DELBA_T;
typedef EVENT_CHECK_REORDER_BUBBLE_T *P_EVENT_CHECK_REORDER_BUBBLE_T;
typedef EVENT_BSS_ABSENCE_PRESENCE_T *P_EVENT_BSS_ABSENCE_PRESENCE_T;
typedef EVENT_STA_CHANGE_PS_MODE_T *P_EVENT_STA_CHANGE_PS_MODE_T;
typedef EVENT_STA_UPDATE_FREE_QUOTA_T *P_EVENT_STA_UPDATE_FREE_QUOTA_T;
#endif
