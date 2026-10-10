// SPDX-License-Identifier: GPL-2.0
/*
 * gemini-wifi-ref-v10 observer. See include/gwref10.h.
 *
 * Synchronisation: one spinlock covers the state, the deadline, the record
 * number and every counter, and is held across the single printk of each
 * record. Seal takes the same lock, clears the armed state and prints the
 * count snapshot, so every admitted record precedes the seal line in the
 * kernel log and no record is counted or printed after it. The unlocked
 * state read before formatting is only an early exit; the locked check
 * decides admission. The deadline is checked on every admission, filtered
 * count and parameter write, so an idle driver past the deadline is sealed
 * by whichever call comes first.
 */
#if defined(GWREF10_HOST_CORE) || defined(GWREF10_HOST_VENDOR)
#include "gwref10-host.h"
#else
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/spinlock.h>
#include <linux/jiffies.h>
#include <linux/printk.h>
#include <linux/string.h>
#include <linux/errno.h>
#include "precomp.h"
#include "que_mgt.h"
#include "gwref10.h"
#endif

#define GWREF10_DEADLINE_SECONDS 240
/* Longest format (rxd) with every field at its maximum is under 200 bytes. */
#define GWREF10_LINE 256

static const char *const gwref10_names[GWREF10_CATEGORIES] = {
	"cmd", "event", "credit", "rxd", "txd", "state"
};

static const unsigned int gwref10_caps[GWREF10_CATEGORIES] = {
	512, 1024, 1024, 2048, 1024, 256
};

static struct {
	spinlock_t lock;
	unsigned int state;	/* 0 idle, 1 armed, 2 sealed */
	unsigned long deadline;
	unsigned int records;
	unsigned int truncated;
	unsigned int recorded[GWREF10_CATEGORIES];
	unsigned int suppressed[GWREF10_CATEGORIES];
	unsigned int filtered[GWREF10_CATEGORIES];
} gwref10 = {
	.lock = __SPIN_LOCK_UNLOCKED(gwref10.lock),
};

static unsigned int gwref10_param;

int gwref10_armed(void)
{
	return READ_ONCE(gwref10.state) == 1;
}

/* Called with the lock held. */
static void gwref10_seal_locked(const char *reason)
{
	WRITE_ONCE(gwref10.state, 2);
	gwref10_param = 2;
	printk(KERN_INFO "gwref10 seal: reason=%s records=%u truncated=%u"
	       " cmd=%u/%u/%u event=%u/%u/%u credit=%u/%u/%u"
	       " rxd=%u/%u/%u txd=%u/%u/%u state=%u/%u/%u\n",
	       reason, gwref10.records, gwref10.truncated,
	       gwref10.recorded[0], gwref10.suppressed[0], gwref10.filtered[0],
	       gwref10.recorded[1], gwref10.suppressed[1], gwref10.filtered[1],
	       gwref10.recorded[2], gwref10.suppressed[2], gwref10.filtered[2],
	       gwref10.recorded[3], gwref10.suppressed[3], gwref10.filtered[3],
	       gwref10.recorded[4], gwref10.suppressed[4], gwref10.filtered[4],
	       gwref10.recorded[5], gwref10.suppressed[5], gwref10.filtered[5]);
}

/* Called with the lock held; returns nonzero when the observer is no longer armed. */
static int gwref10_expired_locked(void)
{
	if (gwref10.state != 1)
		return 1;
	if (time_after(jiffies, gwref10.deadline)) {
		gwref10_seal_locked("deadline");
		return 1;
	}
	return 0;
}

void gwref10_record(enum gwref10_category category, const char *fmt, ...)
{
	char line[GWREF10_LINE];
	unsigned long flags;
	va_list args;
	unsigned int n;
	int len;

	if (category >= GWREF10_CATEGORIES || !gwref10_armed())
		return;
	va_start(args, fmt);
	len = vsnprintf(line, sizeof(line), fmt, args);
	va_end(args);
	if (len < 0)
		return;

	spin_lock_irqsave(&gwref10.lock, flags);
	if (gwref10_expired_locked())
		goto out;
	if (gwref10.recorded[category] >= gwref10_caps[category]) {
		if (++gwref10.suppressed[category] == 1)
			printk(KERN_INFO "gwref10 cap: %s records=%u\n",
			       gwref10_names[category], gwref10.records);
		goto out;
	}
	n = ++gwref10.records;
	gwref10.recorded[category]++;
	if (len >= (int) sizeof(line)) {
		/* The record is incomplete: mark it so the parser refuses it. */
		gwref10.truncated++;
		strcpy(line + sizeof(line) - 9, " trunc=1");
	}
	printk(KERN_DEBUG "gwref10 %s: n=%u %s\n", gwref10_names[category], n, line);
out:
	spin_unlock_irqrestore(&gwref10.lock, flags);
}

/* A record deliberately not written (beacons, probe responses): counted only. */
void gwref10_filtered(enum gwref10_category category)
{
	unsigned long flags;

	if (category >= GWREF10_CATEGORIES || !gwref10_armed())
		return;
	spin_lock_irqsave(&gwref10.lock, flags);
	if (!gwref10_expired_locked())
		gwref10.filtered[category]++;
	spin_unlock_irqrestore(&gwref10.lock, flags);
}

static int gwref10_set(const char *val, const struct kernel_param *kp)
{
	unsigned long flags;
	unsigned int request;
	int ret = 0;

	(void)kp;
	if (kstrtouint(val, 0, &request))
		return -EINVAL;
	spin_lock_irqsave(&gwref10.lock, flags);
	switch (request) {
	case 1:
		if (gwref10.state != 0) {
			ret = -EBUSY;
			break;
		}
		memset(gwref10.recorded, 0, sizeof(gwref10.recorded));
		memset(gwref10.suppressed, 0, sizeof(gwref10.suppressed));
		memset(gwref10.filtered, 0, sizeof(gwref10.filtered));
		gwref10.records = 0;
		gwref10.truncated = 0;
		gwref10.deadline = jiffies + GWREF10_DEADLINE_SECONDS * HZ;
		printk(KERN_INFO "gwref10 arm: deadline_s=%u caps=%u/%u/%u/%u/%u/%u\n",
		       GWREF10_DEADLINE_SECONDS, gwref10_caps[0], gwref10_caps[1],
		       gwref10_caps[2], gwref10_caps[3], gwref10_caps[4], gwref10_caps[5]);
		WRITE_ONCE(gwref10.state, 1);
		gwref10_param = 1;
		break;
	case 2:
		if (gwref10_expired_locked()) {
			ret = -EBUSY;
			break;
		}
		gwref10_seal_locked("explicit");
		break;
	default:
		ret = -EINVAL;
	}
	spin_unlock_irqrestore(&gwref10.lock, flags);
	return ret;
}

static int gwref10_get(char *buffer, const struct kernel_param *kp)
{
	(void)kp;
	return scnprintf(buffer, 16, "%u\n", READ_ONCE(gwref10.state));
}

static const struct kernel_param_ops gwref10_ops = {
	.set = gwref10_set,
	.get = gwref10_get,
};
module_param_cb(gwref10, &gwref10_ops, &gwref10_param, 0644);
MODULE_PARM_DESC(gwref10, "lifecycle observer: write 1 to arm once, 2 to seal; reads the state");

#ifndef GWREF10_HOST_CORE

static const char *const gwref10_class_names[] = {
	"bss", "own", "bcast", "zero", "group", "other"
};

static enum gwref10_class gwref10_classify(P_ADAPTER_T prAdapter, UINT_8 ucBssIndex,
					  const UINT_8 *address)
{
	static const UINT_8 bcast[MAC_ADDR_LEN] = { 0xff, 0xff, 0xff, 0xff, 0xff, 0xff };
	static const UINT_8 zero[MAC_ADDR_LEN] = { 0 };

	if (ucBssIndex < HW_BSSID_NUM && prAdapter->aprBssInfo[ucBssIndex]) {
		P_BSS_INFO_T prBssInfo = prAdapter->aprBssInfo[ucBssIndex];

		if (EQUAL_MAC_ADDR(address, prBssInfo->aucBSSID))
			return GWREF10_PEER_BSS;
		if (EQUAL_MAC_ADDR(address, prBssInfo->aucOwnMacAddr))
			return GWREF10_PEER_OWN;
	}
	if (EQUAL_MAC_ADDR(address, bcast))
		return GWREF10_PEER_BCAST;
	if (EQUAL_MAC_ADDR(address, zero))
		return GWREF10_PEER_ZERO;
	if (IS_BMCAST_MAC_ADDR(address))
		return GWREF10_PEER_GROUP;
	return GWREF10_PEER_OTHER;
}

/* nicTxCmd, after the WIFI_CMD_T header is complete; every command type. */
void gwref10_cmd(P_ADAPTER_T prAdapter, P_CMD_INFO_T prCmdInfo)
{
	P_WIFI_CMD_T prWifiCmd;
	UINT_16 u2Len = prCmdInfo->u2InfoBufLen;

	if (!gwref10_armed())
		return;
	if (prCmdInfo->eCmdType != COMMAND_TYPE_NETWORK_IOCTL &&
	    prCmdInfo->eCmdType != COMMAND_TYPE_GENERAL_IOCTL) {
		gwref10_record(GWREF10_CMD, "type=%u frame=1 len=%u bss=%u sta=%u",
			       (unsigned int) prCmdInfo->eCmdType, u2Len,
			       prCmdInfo->ucBssIndex, prCmdInfo->ucStaRecIndex);
		return;
	}
	/* The header is read only when the buffer exists and covers it. */
	if (!prCmdInfo->pucInfoBuffer || u2Len < sizeof(WIFI_CMD_T)) {
		gwref10_record(GWREF10_CMD, "type=%u short=1 len=%u bss=%u",
			       (unsigned int) prCmdInfo->eCmdType, u2Len, prCmdInfo->ucBssIndex);
		return;
	}
	prWifiCmd = (P_WIFI_CMD_T) prCmdInfo->pucInfoBuffer;
	gwref10_record(GWREF10_CMD, "cid=0x%02x seq=%u set=%u len=%u bss=%u type=%u",
		       prWifiCmd->ucCID, prWifiCmd->ucSeqNum, prWifiCmd->ucSetQuery,
		       u2Len, prCmdInfo->ucBssIndex, (unsigned int) prCmdInfo->eCmdType);
	u2Len -= sizeof(WIFI_CMD_T);
	switch (prWifiCmd->ucCID) {
	case CMD_ID_ADD_REMOVE_KEY:
		/* Metadata bytes precede aucKeyMaterial; the material and the RSC are never read. */
		if (u2Len >= OFFSET_OF(CMD_802_11_KEY, aucKeyMaterial)) {
			P_CMD_802_11_KEY prKey = (P_CMD_802_11_KEY) prWifiCmd->aucBuffer;

			gwref10_record(GWREF10_CMD,
				       "key seq=%u addremove=%u tx=%u keytype=%u auth=%u bss=%u alg=%u keyid=%u keylen=%u wlan=%u peer=%s",
				       prWifiCmd->ucSeqNum, prKey->ucAddRemove, prKey->ucTxKey,
				       prKey->ucKeyType, prKey->ucIsAuthenticator, prKey->ucBssIdx,
				       prKey->ucAlgorithmId, prKey->ucKeyId, prKey->ucKeyLen,
				       prKey->ucWlanIndex,
				       gwref10_class_names[gwref10_classify(prAdapter, prKey->ucBssIdx,
									   prKey->aucPeerAddr)]);
		}
		break;
	case CMD_ID_BSS_ACTIVATE_CTRL:
		if (u2Len >= sizeof(CMD_BSS_ACTIVATE_CTRL)) {
			P_CMD_BSS_ACTIVATE_CTRL p = (P_CMD_BSS_ACTIVATE_CTRL) prWifiCmd->aucBuffer;

			gwref10_record(GWREF10_CMD, "bss seq=%u bss=%u active=%u nettype=%u ownmac=%u bmcwlan=%u",
				       prWifiCmd->ucSeqNum, p->ucBssIndex, p->ucActive, p->ucNetworkType,
				       p->ucOwnMacAddrIndex, p->ucBMCWlanIndex);
		}
		break;
	case CMD_ID_UPDATE_STA_RECORD:
		if (u2Len >= sizeof(CMD_UPDATE_STA_RECORD_T)) {
			P_CMD_UPDATE_STA_RECORD_T p = (P_CMD_UPDATE_STA_RECORD_T) prWifiCmd->aucBuffer;

			gwref10_record(GWREF10_CMD,
				       "sta seq=%u sta=%u statype=%u bss=%u state=%u qos=%u aid=%u wlan=%u bmcwlan=%u resp=%u",
				       prWifiCmd->ucSeqNum, p->ucStaIndex, p->ucStaType, p->ucBssIndex,
				       p->ucStaState, p->ucIsQoS, p->u2AssocId, p->ucWlanIndex,
				       p->ucBMCWlanIndex, p->ucNeedResp);
		}
		break;
	case CMD_ID_REMOVE_STA_RECORD:
		if (u2Len >= sizeof(CMD_REMOVE_STA_RECORD_T)) {
			P_CMD_REMOVE_STA_RECORD_T p = (P_CMD_REMOVE_STA_RECORD_T) prWifiCmd->aucBuffer;

			gwref10_record(GWREF10_CMD, "starm seq=%u action=%u sta=%u bss=%u",
				       prWifiCmd->ucSeqNum, p->ucActionType, p->ucStaIndex, p->ucBssIndex);
		}
		break;
	case CMD_ID_SET_BSS_INFO:
		/* SSID and addresses inside the struct are never read. */
		if (u2Len >= sizeof(CMD_SET_BSS_INFO)) {
			P_CMD_SET_BSS_INFO p = (P_CMD_SET_BSS_INFO) prWifiCmd->aucBuffer;

			gwref10_record(GWREF10_CMD,
				       "bssinfo seq=%u bss=%u connstate=%u opmode=%u qbss=%u staofap=%u authmode=%u encstatus=%u physet=%u bmcwlan=%u",
				       prWifiCmd->ucSeqNum, p->ucBssIndex, p->ucConnectionState,
				       p->ucCurrentOPMode, p->ucIsQBSS, p->ucStaRecIdxOfAP, p->ucAuthMode,
				       p->ucEncStatus, p->ucPhyTypeSet, p->ucBMCWlanIndex);
		}
		break;
	default:
		break;
	}
}

/*
 * The three HIF ingress paths (nicRxReadBuffer, nicRxEnhanceReadBuffer,
 * nicRxSDIOAggReceiveRFBs) store the byte count the HIF delivered for this
 * buffer before any descriptor field is interpreted. The receive helpers
 * below read payload bytes only within that count.
 */
void gwref10_rx_ingress(P_SW_RFB_T prSwRfb, unsigned int hif_bytes)
{
	prSwRfb->u2GwrefHifLen = hif_bytes > 0xffff ? 0xffff : (UINT_16) hif_bytes;
}

/* Nonzero when the descriptor's byte count is covered by what the HIF delivered. */
static int gwref10_rx_valid(P_SW_RFB_T prSwRfb, unsigned int declared)
{
	return declared <= prSwRfb->u2GwrefHifLen && prSwRfb->u2GwrefHifLen <= CFG_RX_MAX_PKT_SIZE;
}

/*
 * nicRxProcessEventPacket, before the dispatcher. Header fields are read only
 * when the HIF delivered the 8-byte header; payload fields only for the
 * allow-listed ids whose declared length is covered by the delivered bytes
 * and covers the pinned structure. Everything else is header-only.
 */
void gwref10_event(P_ADAPTER_T prAdapter, P_SW_RFB_T prSwRfb)
{
	P_WIFI_EVENT_T prEvent = (P_WIFI_EVENT_T) prSwRfb->pucRecvBuff;
	const UINT_8 *body = prEvent->aucBuffer;
	UINT_16 u2Declared, u2Body;

	if (!gwref10_armed())
		return;
	if (prSwRfb->u2GwrefHifLen < EVENT_HDR_SIZE) {
		gwref10_record(GWREF10_EVENT, "shorthdr=1 hif=%u", prSwRfb->u2GwrefHifLen);
		return;
	}
	u2Declared = prEvent->u2PacketLength;
	gwref10_record(GWREF10_EVENT, "eid=0x%02x seq=%u len=%u hif=%u", prEvent->ucEID,
		       prEvent->ucSeqNum, u2Declared, prSwRfb->u2GwrefHifLen);
	if (u2Declared < EVENT_HDR_SIZE || !gwref10_rx_valid(prSwRfb, u2Declared)) {
		gwref10_record(GWREF10_EVENT, "eid=0x%02x seq=%u badlen=1", prEvent->ucEID, prEvent->ucSeqNum);
		return;
	}
	u2Body = u2Declared - EVENT_HDR_SIZE;
#define GWREF10_BODY(type) (u2Body >= sizeof(type))
#define GWREF10_WHOLE(type) (u2Declared >= sizeof(type))
	switch (prEvent->ucEID) {
	case EVENT_ID_ADD_PKEY_DONE:
		/* The payload names no key type, key index or command sequence. */
		if (GWREF10_BODY(EVENT_ADD_KEY_DONE_INFO)) {
			P_EVENT_ADD_KEY_DONE_INFO p = (P_EVENT_ADD_KEY_DONE_INFO) body;

			gwref10_record(GWREF10_EVENT, "keydone seq=%u bss=%u sta=%s", prEvent->ucSeqNum,
				       p->ucBSSIndex,
				       gwref10_class_names[gwref10_classify(prAdapter, p->ucBSSIndex, p->aucStaAddr)]);
		}
		break;
	case EVENT_ID_TX_DONE:
		if (GWREF10_BODY(EVENT_TX_DONE_T)) {
			P_EVENT_TX_DONE_T p = (P_EVENT_TX_DONE_T) body;

			gwref10_record(GWREF10_EVENT, "txdone seq=%u pid=%u status=%u sn=%u wlan=%u count=%u rate=%u flag=%u",
				       prEvent->ucSeqNum, p->ucPacketSeq, p->ucStatus, p->u2SequenceNumber,
				       p->ucWlanIndex, p->ucTxCount, p->u2TxRate, p->ucFlag);
		}
		break;
	case EVENT_ID_ACTIVATE_STA_REC:
		if (GWREF10_BODY(EVENT_ACTIVATE_STA_REC_T)) {
			P_EVENT_ACTIVATE_STA_REC_T p = (P_EVENT_ACTIVATE_STA_REC_T) body;

			gwref10_record(GWREF10_EVENT, "starec seq=%u sta=%u bss=%u peer=%s", prEvent->ucSeqNum,
				       p->ucStaRecIdx, p->ucBssIndex,
				       gwref10_class_names[gwref10_classify(prAdapter, p->ucBssIndex, p->aucMacAddr)]);
		}
		break;
	case EVENT_ID_LINK_QUALITY:
		if (GWREF10_BODY(EVENT_LINK_QUALITY_EX)) {
			P_EVENT_LINK_QUALITY_EX p = (P_EVENT_LINK_QUALITY_EX) body;

			gwref10_record(GWREF10_EVENT, "linkq seq=%u rdy=%u speed=%u busy=%u", prEvent->ucSeqNum,
				       p->ucIsLQ0Rdy, p->u2LinkSpeed, p->ucMediumBusyPercentage);
		}
		break;
	case EVENT_ID_SCAN_DONE:
		if (GWREF10_BODY(EVENT_SCAN_DONE)) {
			P_EVENT_SCAN_DONE p = (P_EVENT_SCAN_DONE) body;

			gwref10_record(GWREF10_EVENT, "scandone seq=%u scanseq=%u sparse=%u", prEvent->ucSeqNum,
				       p->ucSeqNum, p->ucSparseChannelValid);
		}
		break;
	case EVENT_ID_CH_PRIVILEGE:
		if (GWREF10_BODY(EVENT_CH_PRIVILEGE_T)) {
			P_EVENT_CH_PRIVILEGE_T p = (P_EVENT_CH_PRIVILEGE_T) body;

			gwref10_record(GWREF10_EVENT,
				       "chpriv seq=%u bss=%u token=%u status=%u channel=%u band=%u width=%u reqtype=%u grant_ms=%u",
				       prEvent->ucSeqNum, p->ucBssIndex, p->ucTokenID, p->ucStatus, p->ucPrimaryChannel,
				       p->ucRfBand, p->ucRfChannelWidth, p->ucReqType, p->u4GrantInterval);
		}
		break;
	case EVENT_ID_BSS_BEACON_TIMEOUT:
		if (GWREF10_BODY(EVENT_BSS_BEACON_TIMEOUT_T)) {
			P_EVENT_BSS_BEACON_TIMEOUT_T p = (P_EVENT_BSS_BEACON_TIMEOUT_T) body;

			gwref10_record(GWREF10_EVENT, "bcntimeout seq=%u bss=%u reason=%u", prEvent->ucSeqNum,
				       p->ucBssIndex, p->ucReasonCode);
		}
		break;
	case EVENT_ID_STA_AGING_TIMEOUT:
		if (GWREF10_BODY(EVENT_STA_AGING_TIMEOUT_T)) {
			P_EVENT_STA_AGING_TIMEOUT_T p = (P_EVENT_STA_AGING_TIMEOUT_T) body;

			gwref10_record(GWREF10_EVENT, "aging seq=%u sta=%u", prEvent->ucSeqNum, p->ucStaRecIdx);
		}
		break;
	/* The queue-management events declare the 8-byte header inside their structs. */
	case EVENT_ID_RX_ADDBA:
		if (GWREF10_WHOLE(EVENT_RX_ADDBA_T)) {
			P_EVENT_RX_ADDBA_T p = (P_EVENT_RX_ADDBA_T) prEvent;

			gwref10_record(GWREF10_EVENT, "addba seq=%u sta=%u token=%u param=0x%04x timeout=%u ssn=0x%04x",
				       prEvent->ucSeqNum, p->ucStaRecIdx, p->ucDialogToken, p->u2BAParameterSet,
				       p->u2BATimeoutValue, p->u2BAStartSeqCtrl);
		}
		break;
	case EVENT_ID_RX_DELBA:
		if (GWREF10_WHOLE(EVENT_RX_DELBA_T)) {
			P_EVENT_RX_DELBA_T p = (P_EVENT_RX_DELBA_T) prEvent;

			gwref10_record(GWREF10_EVENT, "delba seq=%u sta=%u tid=%u", prEvent->ucSeqNum,
				       p->ucStaRecIdx, p->ucTid);
		}
		break;
	case EVENT_ID_CHECK_REORDER_BUBBLE:
		if (GWREF10_WHOLE(EVENT_CHECK_REORDER_BUBBLE_T)) {
			P_EVENT_CHECK_REORDER_BUBBLE_T p = (P_EVENT_CHECK_REORDER_BUBBLE_T) prEvent;

			gwref10_record(GWREF10_EVENT, "bubble seq=%u sta=%u tid=%u", prEvent->ucSeqNum,
				       p->ucStaRecIdx, p->ucTid);
		}
		break;
	case EVENT_ID_BSS_ABSENCE_PRESENCE:
		if (GWREF10_WHOLE(EVENT_BSS_ABSENCE_PRESENCE_T)) {
			P_EVENT_BSS_ABSENCE_PRESENCE_T p = (P_EVENT_BSS_ABSENCE_PRESENCE_T) prEvent;

			gwref10_record(GWREF10_EVENT, "absence seq=%u bss=%u absent=%u quota=%u", prEvent->ucSeqNum,
				       p->ucBssIndex, p->ucIsAbsent, p->ucBssFreeQuota);
		}
		break;
	case EVENT_ID_STA_CHANGE_PS_MODE:
		if (GWREF10_WHOLE(EVENT_STA_CHANGE_PS_MODE_T)) {
			P_EVENT_STA_CHANGE_PS_MODE_T p = (P_EVENT_STA_CHANGE_PS_MODE_T) prEvent;

			gwref10_record(GWREF10_EVENT, "psmode seq=%u sta=%u inps=%u mode=%u quota=%u", prEvent->ucSeqNum,
				       p->ucStaRecIdx, p->ucIsInPs, p->ucUpdateMode, p->ucFreeQuota);
		}
		break;
	case EVENT_ID_STA_UPDATE_FREE_QUOTA:
		if (GWREF10_WHOLE(EVENT_STA_UPDATE_FREE_QUOTA_T)) {
			P_EVENT_STA_UPDATE_FREE_QUOTA_T p = (P_EVENT_STA_UPDATE_FREE_QUOTA_T) prEvent;

			gwref10_record(GWREF10_EVENT, "quota seq=%u sta=%u mode=%u quota=%u", prEvent->ucSeqNum,
				       p->ucStaRecIdx, p->ucUpdateMode, p->ucFreeQuota);
		}
		break;
	default:
		/* Header only: debug, memory, PMKID, association, scan result, statistics, drop-SN and unknown ids. */
		break;
	}
#undef GWREF10_BODY
#undef GWREF10_WHOLE
}

/* nicTxReleaseResource, after the free counts are updated; only nonzero releases. */
void gwref10_credit(const UINT_16 *released, const TX_TCQ_STATUS_T *tcq)
{
	unsigned int i, any = 0;

	if (!gwref10_armed())
		return;
	for (i = 0; i < TC_NUM; i++)
		any |= released[i];
	if (!any)
		return;
	gwref10_record(GWREF10_CREDIT,
		       "rel0=%u rel1=%u rel2=%u rel3=%u rel4=%u rel5=%u free0=%u free1=%u free2=%u free3=%u free4=%u free5=%u",
		       released[0], released[1], released[2], released[3], released[4], released[5],
		       tcq->au2FreePageCount[0], tcq->au2FreePageCount[1], tcq->au2FreePageCount[2],
		       tcq->au2FreePageCount[3], tcq->au2FreePageCount[4], tcq->au2FreePageCount[5]);
}

/*
 * nicRxFillRFB, after the descriptor fields are parsed. Only the 16-byte
 * descriptor and, within the delivered bytes, the frame-control word and the
 * destination's group bit of an untranslated header of at least 24 bytes, or
 * the Ethernet type of a translated header of at least 14 bytes. Beacons and
 * probe responses are counted as filtered, not recorded.
 */
void gwref10_rxd(P_SW_RFB_T prSwRfb)
{
	P_HW_MAC_RX_DESC_T d = prSwRfb->prRxStatus;
	const UINT_8 *hdr = (const UINT_8 *) prSwRfb->pvHeader;
	unsigned int trans, fc = 0, grp = 0, eth = 0, have_fc = 0, declared;

	if (!gwref10_armed())
		return;
	if (prSwRfb->u2GwrefHifLen < sizeof(HW_MAC_RX_DESC_T)) {
		gwref10_record(GWREF10_RXD, "shortdesc=1 hif=%u", prSwRfb->u2GwrefHifLen);
		return;
	}
	declared = HAL_RX_STATUS_GET_RX_BYTE_CNT(d);
	if (!gwref10_rx_valid(prSwRfb, declared)) {
		gwref10_record(GWREF10_RXD, "badlen=1 declared=%u hif=%u", declared, prSwRfb->u2GwrefHifLen);
		return;
	}
	trans = HAL_RX_STATUS_IS_HEADER_TRAN(d) ? 1 : 0;
	if (!trans && prSwRfb->u2PacketLen >= 24) {
		fc = hdr[0] | (hdr[1] << 8);
		grp = hdr[4] & 1;
		have_fc = 1;
		if ((fc & (MASK_FC_TYPE | MASK_FC_SUBTYPE)) == MAC_FRAME_BEACON ||
		    (fc & (MASK_FC_TYPE | MASK_FC_SUBTYPE)) == MAC_FRAME_PROBE_RSP) {
			gwref10_filtered(GWREF10_RXD);
			return;
		}
	} else if (trans && prSwRfb->u2PacketLen >= 14) {
		eth = (hdr[12] << 8) | hdr[13];
		grp = hdr[0] & 1;
	}
	gwref10_record(GWREF10_RXD,
		       "type=%u len=%u hdrlen=%u pad=%u trans=%u bssid=%u wlan=%u tid=%u sec=%u mismatch=%u fmt=%u uc2me=%u mc=%u bc=%u grp=%u fc=0x%04x havefc=%u eth=0x%04x",
		       (unsigned int) HAL_RX_STATUS_GET_PKT_TYPE(d), prSwRfb->u2PacketLen,
		       (unsigned int) HAL_RX_STATUS_GET_HEADER_LEN(d),
		       (unsigned int) HAL_RX_STATUS_GET_HEADER_OFFSET(d), trans,
		       (unsigned int) HAL_RX_STATUS_GET_BSSID(d), (unsigned int) HAL_RX_STATUS_GET_WLAN_IDX(d),
		       (unsigned int) HAL_RX_STATUS_GET_TID(d), (unsigned int) HAL_RX_STATUS_GET_SEC_MODE(d),
		       HAL_RX_STATUS_IS_CIPHER_MISMATCH(d) ? 1 : 0,
		       (unsigned int) HAL_RX_STATUS_GET_PAYLOAD_FORMAT(d),
		       HAL_RX_STATUS_IS_UC2ME(d) ? 1 : 0, HAL_RX_STATUS_IS_MC(d) ? 1 : 0,
		       HAL_RX_STATUS_IS_BC(d) ? 1 : 0, grp, fc, have_fc, eth);
}

/*
 * nicTxComposeDesc and nicTxComposeSecurityFrameDesc, after the descriptor
 * is complete. The protection bit is the composed descriptor's own; the
 * class (eapol, mgmt, data) is the MSDU's type and is reported separately.
 */
void gwref10_txd(P_MSDU_INFO_T prMsduInfo, P_HW_MAC_TX_DESC_T prTxDesc, int security)
{
	const char *cls;

	if (!gwref10_armed())
		return;
	if (prMsduInfo->fgIs802_1x)
		cls = "eapol";
	else if (prMsduInfo->ucPacketType == TX_PACKET_TYPE_MGMT || security)
		cls = "mgmt";
	else
		cls = "data";
	gwref10_record(GWREF10_TXD, "cls=%s pid=%u wlan=%u bss=%u sta=%u len=%u fmt=%u tid=%u prot=%u is80211=%u tc=%u",
		       cls, prMsduInfo->ucPID, prMsduInfo->ucWlanIndex, prMsduInfo->ucBssIndex,
		       prMsduInfo->ucStaRecIndex, prMsduInfo->u2FrameLength,
		       (unsigned int) HAL_MAC_TX_DESC_GET_HEADER_FORMAT(prTxDesc),
		       (unsigned int) HAL_MAC_TX_DESC_GET_TID(prTxDesc),
		       HAL_MAC_TX_DESC_IS_PROTECTION(prTxDesc) ? 1 : 0,
		       prMsduInfo->fgIs802_11 ? 1 : 0, prMsduInfo->ucTC);
}

void gwref10_sta_state(const STA_RECORD_T *prStaRec, unsigned int new_state)
{
	if (!gwref10_armed())
		return;
	gwref10_record(GWREF10_STATE, "stastate sta=%u wlan=%u bss=%u from=%u to=%u",
		       prStaRec->ucIndex, prStaRec->ucWlanIndex, prStaRec->ucBssIndex,
		       prStaRec->ucStaState, new_state);
}

void gwref10_sta_free(const STA_RECORD_T *prStaRec)
{
	if (!gwref10_armed())
		return;
	gwref10_record(GWREF10_STATE, "stafree sta=%u wlan=%u bss=%u state=%u",
		       prStaRec->ucIndex, prStaRec->ucWlanIndex, prStaRec->ucBssIndex, prStaRec->ucStaState);
}

void gwref10_bss_deactivate(unsigned int bss_index)
{
	if (!gwref10_armed())
		return;
	gwref10_record(GWREF10_STATE, "bssdeact bss=%u", bss_index);
}

#endif /* !GWREF10_HOST_CORE */
