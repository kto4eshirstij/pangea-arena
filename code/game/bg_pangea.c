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

/*
Fields: id, weapon, alt, modes, prim, flags, damage, refire, cooldown, range, speed,
ammo, effectTime, kind, mod, kin, effectValue, name.
*/
#define T( id, w, alt, modes, prim, flags, dmg, refire, cd, range, speed, ammo, eff, kind, mod, kin, val, name ) \
	{ id, w, alt, modes, prim, flags, dmg, refire, cd, range, speed, ammo, eff, kind, mod, kin, val, name }
#define SUN		( PANGEA_FAITH_SUN + 1 )
#define MOON	( PANGEA_FAITH_MOON + 1 )
#define HEARTH	( PANGEA_FAITH_HEARTH + 1 )
#define R( r )	( PANGEA_RACE_##r + 1 )

const pangeaAbility_t bg_pangeaAbilities[] = {
	// 1 тело
	T( "punch",         WP_GAUNTLET, qfalse, ALL, PP_MELEE, 0,            12,  350,    0,  44,    0, 0,    0, PK_NONE, MOD_PANGEA_PUNCH, 0, 0, "удар кулаком" ),
	T( "kick",          WP_GAUNTLET, qtrue,  H,   PP_MELEE, PAF_KNOCK,    10,  600, 3000,  52,    0, 0,    0, PK_NONE, MOD_PANGEA_KICK, 0, 0, "пинок" ),
	T( "headbutt",      WP_GAUNTLET, qtrue,  S,   PP_MELEE, PAF_STUN,     10,  600, 6000,  40,    0, 0,  800, PK_NONE, MOD_PANGEA_HEADBUTT, 0, 0, "удар головой" ),
	// 2 палица
	T( "club",          WP_MACHINEGUN, qfalse, ALL, PP_MELEE, PAF_ARC,    28,  650,    0,  64,    0, 0,    0, PK_NONE, MOD_PANGEA_CLUB, 0, 0, "размах" ),
	T( "club_overhead", WP_MACHINEGUN, qtrue,  ALL, PP_MELEE, PAF_KNOCK,  50, 1100, 4000,  64,    0, 0,    0, PK_NONE, MOD_PANGEA_CLUB, 0, 0, "удар сверху" ),
	// 3 копьё
	T( "spear",         WP_SHOTGUN, qfalse, ALL, PP_MELEE, 0,             32,  800,    0,  96,    0, 0,    0, PK_NONE, MOD_PANGEA_SPEAR, 0, 0, "укол" ),
	T( "spear_throw",   WP_SHOTGUN, qtrue,  ALL, PP_MISSILE, PAF_USES_ITEM, 70, 900, 1000,  0, 1500, 1,    0, PK_SPEAR, MOD_PANGEA_SPEAR_THROW, 0, 0, "бросок копья" ),
	// 4 камень, праща, бола
	T( "sling",         WP_GRENADE_LAUNCHER, qfalse, ALL, PP_MISSILE, 0,  30,  900,    0,   0, 1800, 1,    0, PK_STONE, MOD_PANGEA_STONE, 0, 0, "праща" ),
	T( "stone_throw",   WP_GRENADE_LAUNCHER, qtrue,  H,   PP_MISSILE, 0,  18,  450,    0,   0, 1100, 1,    0, PK_STONE, MOD_PANGEA_STONE, 0, 0, "камень рукой" ),
	T( "bola",          WP_GRENADE_LAUNCHER, qtrue,  S,   PP_MISSILE, PAF_ENTANGLE, 5, 700, 8000, 0, 1100, 0, 2000, PK_BOLA, MOD_PANGEA_BOLA, 0, 0, "бола" ),
	// 5 лук
	T( "arrow",         WP_ROCKET_LAUNCHER, qfalse, ALL, PP_MISSILE, 0,   45, 1000,    0,   0, 2600, 1,    0, PK_ARROW, MOD_PANGEA_ARROW, 0, 0, "выстрел" ),
	T( "arrow_lob",     WP_ROCKET_LAUNCHER, qtrue,  H,   PP_MISSILE, PAF_LOB, 40, 1000, 1500, 0, 2000, 1,  0, PK_ARROW, MOD_PANGEA_ARROW, 0, 0, "навесной" ),
	T( "arrow_fire",    WP_ROCKET_LAUNCHER, qtrue,  S,   PP_MISSILE, PAF_BURN, 35, 1000, 6000, 0, 2400, 1, 3000, PK_ARROW_FIRE, MOD_PANGEA_FIRE_ARROW, 0, 0, "огненная стрела" ),
	// 6 факел (только бойня)
	T( "torch",         WP_LIGHTNING, qfalse, S, PP_MELEE, PAF_BURN,      18,  700,    0,  64,    0, 0, 2000, PK_NONE, MOD_PANGEA_TORCH, 0, 0, "удар факелом" ),
	T( "brand_throw",   WP_LIGHTNING, qtrue,  S, PP_MISSILE, PAF_BURN|PAF_BOUNCE|PAF_USES_ITEM, 20, 800, 8000, 0, 900, 1, 3000, PK_BRAND, MOD_PANGEA_BRAND, 0, 0, "бросок головни" ),
	// 7 щит
	T( "block",         WP_RAILGUN, qfalse, ALL, PP_BLOCK, 0,              0,    0,    0,   0,    0, 0,    0, PK_NONE, MOD_UNKNOWN, 0, 0, "блок" ),
	T( "slam",          WP_RAILGUN, qtrue,  ALL, PP_SLAM, PAF_KNOCK,       8,  600, 7000,   0,    0, 0,    0, PK_NONE, MOD_PANGEA_SLAM, 0, 0, "удар о землю" ),

	// 8 обряды веры (C7): primary and secondary share the slot's cooldown
	T( "sun_heat",      WP_PLASMAGUN, qfalse, H, PP_CONE, 0,              14,  600, 6000, 200,    0, 0,    0, PK_NONE, MOD_PANGEA_RITE, SUN, 0, "Жар" ),
	T( "sun_heat",      WP_PLASMAGUN, qfalse, S, PP_CONE, PAF_BURN,       14,  600, 6000, 200,    0, 0, 1500, PK_NONE, MOD_PANGEA_RITE, SUN, 0, "Жар" ),
	T( "sun_endure",    WP_PLASMAGUN, qtrue,  ALL, PP_SELF, PAF_WARD,      0,  400, 18000,  0,    0, 0, 5000, PK_NONE, MOD_UNKNOWN, SUN, 50, "Стойкость" ),
	T( "moon_fog",      WP_PLASMAGUN, qfalse, ALL, PP_CLOUD, 0,            0,  500, 12000, 600,   0, 0, 7000, PK_FOG, MOD_UNKNOWN, MOON, 0, "Морок" ),
	T( "moon_vision",   WP_PLASMAGUN, qtrue,  ALL, PP_SELF, PAF_VISION,    0,  400, 20000,  0,    0, 0, 6000, PK_NONE, MOD_UNKNOWN, MOON, 0, "Видение" ),
	T( "hearth_cry",    WP_PLASMAGUN, qfalse, H, PP_RING, PAF_KNOCK,       6,  600, 10000, 180,   0, 0,    0, PK_NONE, MOD_PANGEA_RITE, HEARTH, 350, "Крик рода" ),
	T( "hearth_cry",    WP_PLASMAGUN, qfalse, S, PP_RING, PAF_KNOCK|PAF_STUN, 6, 600, 10000, 180, 0, 0,  600, PK_NONE, MOD_PANGEA_RITE, HEARTH, 350, "Крик рода" ),
	T( "hearth_spirit", WP_PLASMAGUN, qtrue,  ALL, PP_SELF, PAF_MEND,     30,  400, 22000,  0,    0, 0, 4000, PK_NONE, MOD_UNKNOWN, HEARTH, 0, "Дух предков" ),

	// 9 наследия народов (C7)
	T( "human_grit",    WP_BFG, qfalse, ALL, PP_SELF, PAF_HEAL,           20,  400, 20000,  0,    0, 0,    0, PK_NONE, MOD_UNKNOWN, R( HUMAN ), 0, "Упорство" ),
	T( "elf_step",      WP_BFG, qfalse, ALL, PP_SELF, PAF_SWIFT,           0,  300, 15000,  0,    0, 0, 4000, PK_NONE, MOD_UNKNOWN, R( ELF ), 140, "Лёгкий шаг" ),
	T( "dwarf_stone",   WP_BFG, qfalse, ALL, PP_SELF, PAF_WARD,            0,  400, 20000,  0,    0, 0, 5000, PK_NONE, MOD_UNKNOWN, R( DWARF ), 50, "Каменная кожа" ),
	T( "gnome_trick",   WP_BFG, qfalse, ALL, PP_SELF, PAF_INVIS,           0,  300, 20000,  0,    0, 0, 3000, PK_NONE, MOD_UNKNOWN, R( GNOME ), 0, "Уловка" ),
	T( "halfling_luck", WP_BFG, qfalse, ALL, PP_SELF, PAF_DODGE,           0,  300, 15000,  0,    0, 0, 5000, PK_NONE, MOD_UNKNOWN, R( HALFLING ), 0, "Удача" ),
	T( "orc_rage",      WP_BFG, qfalse, ALL, PP_SELF, PAF_RAGE,            0,  400, 20000,  0,    0, 0, 5000, PK_NONE, MOD_UNKNOWN, R( ORC ), 130, "Ярость" ),
	T( "goblin_dash",   WP_BFG, qfalse, ALL, PP_SELF, PAF_SWIFT,           0,  300, 12000,  0,    0, 0, 3000, PK_NONE, MOD_UNKNOWN, R( GOBLIN ), 150, "Юркость" ),
	T( "goliath_boulder", WP_BFG, qfalse, ALL, PP_MISSILE, PAF_KNOCK,     50,  900, 10000,  0,  900, 0,    0, PK_BOULDER, MOD_PANGEA_LEGACY, R( GOLIATH ), 0, "Валун" ),
	T( "dragon_breath", WP_BFG, qfalse, H, PP_CONE, 0,                    16,  700, 9000, 220,    0, 0,    0, PK_NONE, MOD_PANGEA_LEGACY, R( DRAGONBORN ), 0, "Дыхание" ),
	T( "dragon_breath", WP_BFG, qfalse, S, PP_CONE, PAF_BURN,             16,  700, 9000, 220,    0, 0, 2000, PK_NONE, MOD_PANGEA_LEGACY, R( DRAGONBORN ), 0, "Дыхание" ),
	T( "tiefling_blink", WP_BFG, qfalse, ALL, PP_BLINK, 0,                 0,  300, 12000, 240,   0, 0,    0, PK_NONE, MOD_UNKNOWN, R( TIEFLING ), 0, "Шаг сквозь тень" ),
	T( "troll_regen",   WP_BFG, qfalse, ALL, PP_SELF, PAF_MEND,           40,  400, 25000,  0,    0, 0, 5000, PK_NONE, MOD_UNKNOWN, R( TROLL ), 0, "Регенерация" ),
	T( "felar_pounce",  WP_BFG, qfalse, ALL, PP_LEAP, 0,                   0,  400, 8000,   0,  280, 0,    0, PK_NONE, MOD_UNKNOWN, R( FELAR ), 520, "Прыжок кошки" ),
	T( "fey_flutter",   WP_BFG, qfalse, ALL, PP_LEAP, PAF_AIR,             0,  300, 7000,   0,  420, 0,    0, PK_NONE, MOD_UNKNOWN, R( FEY ), 180, "Порхание" ),
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
const pangeaAbility_t *BG_PangeaAbility( int weapon, qboolean alt, int mode, int kin ) {
	int bits = BG_PangeaModeBits( mode );
	int i, want = 0;

	if ( !bits ) {
		return NULL;
	}
	if ( weapon == WP_PLASMAGUN ) {
		want = PANGEA_KIN_FAITH( kin ) + 1;
	} else if ( weapon == WP_BFG ) {
		want = PANGEA_KIN_RACE( kin ) + 1;
	}
	for ( i = 0 ; i < bg_numPangeaAbilities ; i++ ) {
		const pangeaAbility_t *a = &bg_pangeaAbilities[i];
		if ( a->weapon == weapon && !a->alt == !alt && ( a->modes & bits ) && ( !a->kin || a->kin == want ) ) {
			return a;
		}
	}
	return NULL;
}

qboolean BG_PangeaSlotAllowed( int weapon, int mode, int kin ) {
	if ( weapon - WP_GAUNTLET >= PANGEA_SLOTS ) {
		return qfalse;
	}
	return BG_PangeaAbility( weapon, qfalse, mode, kin ) != NULL;
}

static const char *bg_pangeaRaces[PANGEA_RACE_NUM] = {
	"human", "elf", "dwarf", "gnome", "halfling", "orc", "goblin", "goliath",
	"dragonborn", "tiefling", "troll", "felar", "fey"
};

int BG_PangeaRaceIndex( const char *race ) {
	int i;

	for ( i = 0 ; i < PANGEA_RACE_NUM ; i++ ) {
		if ( !Q_stricmp( race, bg_pangeaRaces[i] ) ) {
			return i;
		}
	}
	return PANGEA_RACE_HUMAN;
}

const char *BG_PangeaRaceName( int race ) {
	if ( race < 0 || race >= PANGEA_RACE_NUM ) {
		return bg_pangeaRaces[0];
	}
	return bg_pangeaRaces[race];
}

int BG_PangeaFaithIndex( const char *faith ) {
	if ( !Q_stricmp( faith, "sun" ) ) {
		return PANGEA_FAITH_SUN;
	}
	if ( !Q_stricmp( faith, "moon" ) ) {
		return PANGEA_FAITH_MOON;
	}
	return PANGEA_FAITH_HEARTH;
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
	case WP_PLASMAGUN:			return "rite";
	case WP_BFG:				return "legacy";
	default:					return NULL;
	}
}
