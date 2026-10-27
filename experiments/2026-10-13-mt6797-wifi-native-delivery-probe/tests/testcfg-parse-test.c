/* SPDX-License-Identifier: GPL-2.0-only */
/* The per-join test schedule (CONFIG_MT6797_WIFI_TESTCONFIG): the actual
 * testcfg-parse.h. Each entry is applied over the build's configuration,
 * a refused entry keeps its name and reason, and a schedule that does not
 * fit is refused whole. Built by run-testcfg-test.py.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "testcfg-parse.h"

static const struct mt6797_testcfg base = {
	.rate = 0x85, .bw40 = true, .sgi = false, .agg = true, .peek = true,
};

static bool same(const struct mt6797_testcfg *a, unsigned int rate, bool bw40,
		 bool sgi, bool agg, bool peek)
{
	return a->rate == rate && a->bw40 == bw40 && a->sgi == sgi &&
	       a->agg == agg && a->peek == peek;
}

static int parse(const char *s, struct mt6797_testcfg_entry *e)
{
	return mt6797_testcfg_schedule(s, strlen(s), &base, e);
}

int main(void)
{
	struct mt6797_testcfg_entry e[MT6797_TESTCFG_ENTRIES + 1];
	char text[512];
	unsigned int i;

	/* Empty, or blank as echo writes it: no entries, the build throughout. */
	assert(parse("", e) == 0);
	assert(parse(" \n", e) == 0);
	/* The matrix as the owner wrote it, with echo's newline. */
	assert(parse("default,20M7, 40M5 ,40M6,40M5+sgi,agg=0\n", e) == 6);
	assert(!e[0].refused && same(&e[0].cfg, 0x85, true, false, true, true));
	assert(!strcmp(e[0].name, "default"));
	assert(!e[1].refused && same(&e[1].cfg, 0x87, false, false, true, true));
	assert(!e[2].refused && same(&e[2].cfg, 0x85, true, false, true, true));
	assert(!strcmp(e[2].name, "40M5"));
	assert(!e[3].refused && same(&e[3].cfg, 0x86, true, false, true, true));
	assert(!e[4].refused && same(&e[4].cfg, 0x85, true, true, true, true));
	assert(!e[5].refused && same(&e[5].cfg, 0x85, true, false, false, true));
	/* The long forms; each entry starts again from the build. */
	assert(parse("bw=20+rate=fixed:0x87,rate=fixed:0x4b+peek=0,sgi=1+sgi=0,rate=fixed:0xc", e) == 4);
	assert(!e[0].refused && same(&e[0].cfg, 0x87, false, false, true, true));
	assert(!e[1].refused && same(&e[1].cfg, 0x4b, true, false, true, false));
	assert(!e[2].refused && same(&e[2].cfg, 0x85, true, false, true, true));
	assert(!e[3].refused && e[3].cfg.rate == 0x0c);
	/* default later in an entry resets what came before it */
	assert(parse("20M7+default+sgi", e) == 1);
	assert(!e[0].refused && same(&e[0].cfg, 0x85, true, true, true, true));
	/* Refusals keep their place, name and reason; the rest still parse. */
	assert(parse("minstrel:20,rate=minstrel,40M8,rate=fixed:0x0,rate=fixed:0x123,"
		     "rate=fixed:0xg1,agg=2,40m5,,20M7+,+sgi,bw=80,sgi=yes,20M7", e) == 14);
	for (i = 0; i < 13; i++)
		assert(e[i].refused);
	assert(!strcmp(e[0].refused, "minstrel needs per-frame transmit status"));
	assert(!strcmp(e[1].refused, "minstrel needs per-frame transmit status"));
	assert(!strcmp(e[2].refused, "unknown item"));
	assert(!strcmp(e[3].refused, "rate code 0"));
	assert(!strcmp(e[4].refused, "bad rate code"));
	assert(!strcmp(e[5].refused, "bad rate code"));
	assert(!strcmp(e[8].refused, "empty entry") && !e[8].name[0]);
	assert(!strcmp(e[9].refused, "empty item"));
	assert(!strcmp(e[10].refused, "empty item"));
	assert(!strcmp(e[0].name, "minstrel:20"));
	assert(!e[13].refused && same(&e[13].cfg, 0x87, false, false, true, true));
	/* Sixteen entries fit; seventeen, or a name of 32 bytes, do not. */
	text[0] = 0;
	for (i = 0; i < MT6797_TESTCFG_ENTRIES; i++)
		strcat(text, i ? ",40M5" : "40M5");
	assert(parse(text, e) == (int)MT6797_TESTCFG_ENTRIES);
	strcat(text, ",40M5");
	assert(parse(text, e) == -1);
	assert(parse("20M7+20M7+20M7+20M7+20M7+20M7+2", e) == 1);
	assert(parse("20M7+20M7+20M7+20M7+20M7+20M7+20", e) == -1);
	printf("testcfg-parse-test: PASS\n");
	return 0;
}
