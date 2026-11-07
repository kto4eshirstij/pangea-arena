/*
===========================================================================
Pangea Arena: tier-0 ability table. Copyright (C) 2026 Pangea contributors.

This file is part of Pangea Arena, a fork of ioquake3, and is distributed
under the terms of the GNU General Public License version 2 or later
(see COPYING.txt).
===========================================================================

The numbers are a first proposal (C6, 2026-11-07), to be tuned after test duels:
Q3 scale, 100 health, run speed 320 u/s, 1 u ~ 1 inch.
*/

#include "../qcommon/q_shared.h"
#include "bg_public.h"

#define H	PANGEA_MODE_HONOR
#define S	PANGEA_MODE_SLAUGHTER
#define ALL	PANGEA_MODE_ALL

const pangeaAbility_t bg_pangeaAbilities[] = {
//	  id              weapon               alt    modes prim        flags                       dmg refire  cd    range speed ammo eff   kind           mod
	// 1 тело
	{ "punch",        WP_GAUNTLET,         qfalse, ALL, PP_MELEE,   0,                           12,  350,    0,   44,    0, 0,    0, PK_NONE,       MOD_PANGEA_PUNCH },
	{ "kick",         WP_GAUNTLET,         qtrue,  H,   PP_MELEE,   PAF_KNOCK,                   10,  600, 3000,   52,    0, 0,    0, PK_NONE,       MOD_PANGEA_KICK },
	{ "headbutt",     WP_GAUNTLET,         qtrue,  S,   PP_MELEE,   PAF_STUN,                    10,  600, 6000,   40,    0, 0,  800, PK_NONE,       MOD_PANGEA_HEADBUTT },
	// 2 палица
	{ "club",         WP_MACHINEGUN,       qfalse, ALL, PP_MELEE,   PAF_ARC,                     28,  650,    0,   64,    0, 0,    0, PK_NONE,       MOD_PANGEA_CLUB },
	{ "club_overhead",WP_MACHINEGUN,       qtrue,  ALL, PP_MELEE,   PAF_KNOCK,                   50, 1100, 4000,   64,    0, 0,    0, PK_NONE,       MOD_PANGEA_CLUB },
	// 3 копьё
	{ "spear",        WP_SHOTGUN,          qfalse, ALL, PP_MELEE,   0,                           32,  800,    0,   96,    0, 0,    0, PK_NONE,       MOD_PANGEA_SPEAR },
	{ "spear_throw",  WP_SHOTGUN,          qtrue,  ALL, PP_MISSILE, PAF_USES_ITEM,               70,  900, 1000,    0, 1500, 1,    0, PK_SPEAR,      MOD_PANGEA_SPEAR_THROW },
	// 4 камень, праща, бола
	{ "sling",        WP_GRENADE_LAUNCHER, qfalse, ALL, PP_MISSILE, 0,                           30,  900,    0,    0, 1800, 1,    0, PK_STONE,      MOD_PANGEA_STONE },
	{ "stone_throw",  WP_GRENADE_LAUNCHER, qtrue,  H,   PP_MISSILE, 0,                           18,  450,    0,    0, 1100, 1,    0, PK_STONE,      MOD_PANGEA_STONE },
	{ "bola",         WP_GRENADE_LAUNCHER, qtrue,  S,   PP_MISSILE, PAF_ENTANGLE,                 5,  700, 8000,    0, 1100, 0, 2000, PK_BOLA,       MOD_PANGEA_BOLA },
	// 5 лук
	{ "arrow",        WP_ROCKET_LAUNCHER,  qfalse, ALL, PP_MISSILE, 0,                           45, 1000,    0,    0, 2600, 1,    0, PK_ARROW,      MOD_PANGEA_ARROW },
	{ "arrow_lob",    WP_ROCKET_LAUNCHER,  qtrue,  H,   PP_MISSILE, PAF_LOB,                     40, 1000, 1500,    0, 2000, 1,    0, PK_ARROW,      MOD_PANGEA_ARROW },
	{ "arrow_fire",   WP_ROCKET_LAUNCHER,  qtrue,  S,   PP_MISSILE, PAF_BURN,                    35, 1000, 6000,    0, 2400, 1, 3000, PK_ARROW_FIRE, MOD_PANGEA_FIRE_ARROW },
	// 6 факел (только бойня)
	{ "torch",        WP_LIGHTNING,        qfalse, S,   PP_MELEE,   PAF_BURN,                    18,  700,    0,   64,    0, 0, 2000, PK_NONE,       MOD_PANGEA_TORCH },
	{ "brand_throw",  WP_LIGHTNING,        qtrue,  S,   PP_MISSILE, PAF_BURN|PAF_BOUNCE|PAF_USES_ITEM, 20, 800, 8000, 0,  900, 1, 3000, PK_BRAND,      MOD_PANGEA_BRAND },
	// 7 щит
	{ "block",        WP_RAILGUN,          qfalse, ALL, PP_BLOCK,   0,                            0,    0,    0,    0,    0, 0,    0, PK_NONE,       MOD_UNKNOWN },
	{ "slam",         WP_RAILGUN,          qtrue,  ALL, PP_SLAM,    PAF_KNOCK,                    8,  600, 7000,    0,    0, 0,    0, PK_NONE,       MOD_PANGEA_SLAM },
};

const int bg_numPangeaAbilities = ARRAY_LEN( bg_pangeaAbilities );

int BG_PangeaModeBits( int mode ) {
	if ( mode == PANGEA_HONOR ) {
		return PANGEA_MODE_HONOR;
	}
	if ( mode == PANGEA_SLAUGHTER ) {
		return PANGEA_MODE_SLAUGHTER;
	}
	return 0;
}

/*
The ability of a slot in a mode, NULL if the slot has none (or the mode is the simulator).
*/
const pangeaAbility_t *BG_PangeaAbility( int weapon, qboolean alt, int mode ) {
	int bits = BG_PangeaModeBits( mode );
	int i;

	if ( !bits ) {
		return NULL;
	}
	for ( i = 0 ; i < bg_numPangeaAbilities ; i++ ) {
		const pangeaAbility_t *a = &bg_pangeaAbilities[i];
		if ( a->weapon == weapon && !a->alt == !alt && ( a->modes & bits ) ) {
			return a;
		}
	}
	return NULL;
}

qboolean BG_PangeaSlotAllowed( int weapon, int mode ) {
	return BG_PangeaAbility( weapon, qfalse, mode ) != NULL;
}

const char *BG_PangeaSlotId( int weapon ) {
	switch ( weapon ) {
	case WP_GAUNTLET:			return "fists";
	case WP_MACHINEGUN:			return "club";
	case WP_SHOTGUN:			return "spear";
	case WP_GRENADE_LAUNCHER:	return "sling";
	case WP_ROCKET_LAUNCHER:	return "bow";
	case WP_LIGHTNING:			return "torch";
	case WP_RAILGUN:			return "shield";
	default:					return NULL;
	}
}
