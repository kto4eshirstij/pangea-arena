/*
===========================================================================
Pangea Arena: tier-0 abilities ("порог 0", слоты 1–7). Copyright (C) 2026 Pangea contributors.

This file is part of Pangea Arena, a fork of ioquake3, and is distributed
under the terms of the GNU General Public License version 2 or later
(see COPYING.txt).
===========================================================================

Shared by game and cgame (included at the end of bg_public.h).

The seven slots reuse the stock weapon numbers, so keys 1–7, weapon switching,
ammo and the network protocol stay as they are:

  slot 1  WP_GAUNTLET          тело (кулаки)
  slot 2  WP_MACHINEGUN        палица
  slot 3  WP_SHOTGUN           копьё           ammo = копьё в руке (0/1)
  slot 4  WP_GRENADE_LAUNCHER  камень/праща    ammo = голыши
  slot 5  WP_ROCKET_LAUNCHER   лук             ammo = стрелы
  slot 6  WP_LIGHTNING         факел           ammo = факел в руке (0/1)
  slot 7  WP_RAILGUN           щит

Every slot has a primary (+attack) and a secondary (+button12, BUTTON_PANGEA_ALT)
ability. Which ones exist depends on the arena mode (g_pangea_arsenal):

  honor      дуэль чести: no fire, no bola, no stun
  slaughter  бойня: everything
  (anything else = «симулятор», the stock OpenArena weapons, this file is unused)

Secondary cooldowns live in ps->stats[STAT_PANGEA_CD1 + slot - 1] (ms, counted
down by Pmove, so they are predicted). Status effects visible to everybody live
in ps->generic1 / es->generic1 (PSTAT_*). A missile's kind is es->generic1 (PK_*).
*/

#ifndef BG_PANGEA_H
#define BG_PANGEA_H

#define BUTTON_PANGEA_ALT	4096		// +button12 (free bit in usercmd_t.buttons)

// arena modes for Pmove and cgame (pmove_t.pangea, cgs.pangea)
#define PANGEA_SIM			0			// stock weapons
#define PANGEA_HONOR		1
#define PANGEA_SLAUGHTER	2

#define PANGEA_MODE_HONOR		1		// pangeaAbility_t.modes bits
#define PANGEA_MODE_SLAUGHTER	2
#define PANGEA_MODE_ALL			3

// ps->generic1 / es->generic1 of a player
#define PSTAT_BURNING		1
#define PSTAT_ENTANGLED		2
#define PSTAT_STUNNED		4
#define PSTAT_BLOCKING		8
#define PSTAT_TORCH_OUT		16			// the brand was thrown, the hand is empty for a while

// es->generic1 of a Pangea missile / ground entity
typedef enum {
	PK_NONE,
	PK_STONE,
	PK_BOLA,
	PK_ARROW,
	PK_ARROW_FIRE,
	PK_SPEAR,			// thrown spear in flight
	PK_SPEAR_GROUND,	// a spear lying on the ground, pick it up by walking over it
	PK_BRAND,
	PK_FIRE,			// fire patch left by the brand
	PK_NUM
} pangeaKind_t;

typedef enum {
	PP_MELEE,			// trace(s) in front of the player
	PP_MISSILE,			// a projectile (kind)
	PP_BLOCK,			// hold: frontal damage reduced
	PP_SLAM				// leap off the ground with a shock ring
} pangeaPrim_t;

#define PAF_ARC			1		// melee: three traces in a horizontal arc
#define PAF_BURN		2		// sets the target on fire
#define PAF_ENTANGLE	4
#define PAF_STUN		8
#define PAF_KNOCK		16		// strong knockback
#define PAF_LOB			32		// missile: aimed 25 degrees higher
#define PAF_BOUNCE		64		// missile bounces (brand)
#define PAF_USES_ITEM	128		// throws the weapon itself (spear, brand): ammo 1 -> 0

typedef struct {
	const char		*id;			// latin id, also the obituary/log name
	int				weapon;			// WP_* slot
	qboolean		alt;			// secondary ability
	int				modes;			// PANGEA_MODE_* where it exists
	pangeaPrim_t	prim;
	int				flags;			// PAF_*
	int				damage;
	int				refire;			// ms the weapon is busy afterwards
	int				cooldown;		// ms before the secondary can be used again
	int				range;			// melee reach, units
	int				speed;			// missile speed, units/s
	int				ammo;			// ammo it takes (0 = none)
	int				effectTime;		// ms of burn / entangle / stun
	int				kind;			// PK_* of the missile
	int				mod;			// means of death
} pangeaAbility_t;

#define PANGEA_SLOTS		7
#define STAT_PANGEA_CD1		( STAT_MAX_HEALTH + 1 )		// .. CD1 + 6, ms

// player numbers
#define PANGEA_BURN_TICK		500		// ms between burn damage ticks
#define PANGEA_BURN_DAMAGE		4		// per tick
#define PANGEA_FIRE_TIME		5000	// fire patch lifetime
#define PANGEA_FIRE_RADIUS		72
#define PANGEA_TORCH_BACK		8000	// a new torch after the brand is thrown
#define PANGEA_SPEAR_BACK		20000	// a lost spear comes back by itself
#define PANGEA_BLOCK_FACTOR		0.2f	// frontal damage taken while blocking
#define PANGEA_BLOCK_DOT		0.25f	// "frontal": cos of ~75 degrees
#define PANGEA_BLOCK_SPEED		0.6f
#define PANGEA_ENTANGLE_SPEED	0.35f
#define PANGEA_SLAM_UP			480
#define PANGEA_SLAM_FORWARD		300
#define PANGEA_SLAM_RADIUS		110
#define PANGEA_SLAM_PUSH		320
#define PANGEA_STONES_START		10
#define PANGEA_STONES_MAX		25
#define PANGEA_ARROWS_START		8
#define PANGEA_ARROWS_MAX		20
#define PANGEA_MELEE_AMMO		99		// slots without ammo: not -1, bot AI treats -1 as empty

extern const pangeaAbility_t	bg_pangeaAbilities[];
extern const int				bg_numPangeaAbilities;

const pangeaAbility_t	*BG_PangeaAbility( int weapon, qboolean alt, int mode );
qboolean				BG_PangeaSlotAllowed( int weapon, int mode );
int						BG_PangeaModeBits( int mode );
const char				*BG_PangeaSlotId( int weapon );	// "fists" .. "shield" (model ids)

#endif
