/*
===========================================================================
Pangea Arena: tier-0 abilities on the client. Copyright (C) 2026 Pangea contributors.

This file is part of Pangea Arena, a fork of ioquake3, and is distributed
under the terms of the GNU General Public License version 2 or later
(see COPYING.txt).
===========================================================================

Only used when the server runs a tier-0 arena (cgs.pangea, from g_pangea_arsenal
in the serverinfo). Models, hands and skins come from the weapons pak
(docs/weapons/README.md):

  models/weapons2/<id>/<id>.md3, <id>_paint1..4.skin    the weapon, 4 ochre paintings
  models/hands/<small|medium|large>/<pose>.md3           first-person hands in view space
  models/hands/skin/<race>.skin, <race>_fists1..4.skin   skin of the people (+ wraps)
  models/projectiles/*.md3                               missiles and pickups

The models are static (1 frame): swings, thrusts and the draw are done here
procedurally. Painting: (clientNum % 4) + 1, stable for a match.

Sounds are temporary OpenArena ones (GPL) until our own are made.
*/

#include "cg_local.h"

#define Vector4Set( v, a, b, c, d )	( (v)[0] = (a), (v)[1] = (b), (v)[2] = (c), (v)[3] = (d) )

typedef struct {
	qboolean	registered;
	qhandle_t	model;					// the weapon (world + view)
	qhandle_t	paint[4];
	qhandle_t	pose[3];				// hands per build
	sfxHandle_t	swing;
	sfxHandle_t	altSound;
} pangeaSlot_t;

static pangeaSlot_t	pgSlots[WP_NUM_WEAPONS];

static struct {
	qboolean	registered;
	qhandle_t	fistPose[3];
	qhandle_t	stones[4];
	qhandle_t	bola, arrow, arrowFire, brand, spear, atlatl;
	qhandle_t	flameShader;
	sfxHandle_t	hitWall, hitStone, hitFlesh, block, slam, fire, bowRelease, slingRelease, throwSound;
	char		race[24];				// of the local hands
	int			build;
	qhandle_t	handSkin;
	qhandle_t	fistSkin;
} pg;

// the last own swing, for the procedural first-person animation
static int		pgSwingTime;
static int		pgSwingWeapon;
static qboolean	pgSwingAlt;

static const char *pgBuildNames[3] = { "small", "medium", "large" };

/*
small: gnome, halfling, goblin, fey; large: goliath, troll; medium: everybody else
(tools/weapons/hands/poses.py RACE_BUILD).
*/
static int CG_PangeaBuild( const char *race ) {
	if ( !Q_stricmp( race, "gnome" ) || !Q_stricmp( race, "halfling" ) ||
		 !Q_stricmp( race, "goblin" ) || !Q_stricmp( race, "fey" ) ) {
		return 0;
	}
	if ( !Q_stricmp( race, "goliath" ) || !Q_stricmp( race, "troll" ) ) {
		return 2;
	}
	return 1;
}

static qboolean CG_PangeaKnownRace( const char *race ) {
	static const char *races[] = { "human", "elf", "dwarf", "gnome", "halfling", "orc", "goblin",
		"goliath", "dragonborn", "tiefling", "troll", "felar", "fey" };
	int i;

	for ( i = 0 ; i < ARRAY_LEN( races ) ; i++ ) {
		if ( !Q_stricmp( race, races[i] ) ) {
			return qtrue;
		}
	}
	return qfalse;
}

static int CG_PangeaPaint( int clientNum ) {
	return ( clientNum & 3 );		// 0..3 -> _paint1.._paint4
}

static const char *CG_PangeaPoseName( int weapon ) {
	switch ( weapon ) {
	case WP_GAUNTLET:			return "fist";
	case WP_MACHINEGUN:			return "club";
	case WP_SHOTGUN:			return "spear";
	case WP_GRENADE_LAUNCHER:	return "sling";
	case WP_ROCKET_LAUNCHER:	return "bow";
	case WP_LIGHTNING:			return "torch";
	case WP_RAILGUN:			return "shield";
	default:					return "fist";
	}
}

static void CG_PangeaRegisterCommon( void ) {
	int i;

	if ( pg.registered ) {
		return;
	}
	pg.registered = qtrue;
	for ( i = 0 ; i < 3 ; i++ ) {
		pg.fistPose[i] = trap_R_RegisterModel( va( "models/hands/%s/fist.md3", pgBuildNames[i] ) );
	}
	for ( i = 0 ; i < 4 ; i++ ) {
		pg.stones[i] = trap_R_RegisterModel( va( "models/projectiles/proj_stone%i.md3", i + 1 ) );
	}
	pg.bola = trap_R_RegisterModel( "models/projectiles/proj_bola.md3" );
	pg.arrow = trap_R_RegisterModel( "models/projectiles/proj_arrow.md3" );
	pg.arrowFire = trap_R_RegisterModel( "models/projectiles/proj_arrow_fire.md3" );
	pg.brand = trap_R_RegisterModel( "models/projectiles/proj_brand.md3" );
	pg.spear = trap_R_RegisterModel( "models/weapons2/spear/spear.md3" );
	pg.atlatl = trap_R_RegisterModel( "models/weapons2/atlatl/atlatl.md3" );
	pg.flameShader = trap_R_RegisterShader( "models/weapons2/torch/flame" );

	pg.hitWall = trap_S_RegisterSound( "sound/weapons/proxmine/wstbimpl.wav", qfalse );
	pg.hitStone = trap_S_RegisterSound( "sound/weapons/grenade/hgrenb1a.wav", qfalse );
	pg.hitFlesh = trap_S_RegisterSound( "sound/weapons/proxmine/wstbimpd.wav", qfalse );
	pg.block = trap_S_RegisterSound( "sound/weapons/grenade/hgrenb2a.wav", qfalse );
	pg.slam = trap_S_RegisterSound( "sound/weapons/rocket/rocklx1a.wav", qfalse );
	pg.fire = trap_S_RegisterSound( "sound/weapons/lightning/lg_hum.wav", qfalse );
	pg.bowRelease = trap_S_RegisterSound( "sound/weapons/proxmine/wstbfire.wav", qfalse );
	pg.slingRelease = trap_S_RegisterSound( "sound/weapons/grapple/grapfire.wav", qfalse );
	pg.throwSound = trap_S_RegisterSound( "sound/weapons/grapple/grapfire.wav", qfalse );
}

/*
Called at the end of CG_RegisterWeapon: replaces the OpenArena weapon of a slot
by the tier-0 one. Weapons of the simulator (8..) stay as they are.
*/
void CG_PangeaRegisterWeapon( weaponInfo_t *wi, int weaponNum ) {
	pangeaSlot_t	*s;
	const char		*id = BG_PangeaSlotId( weaponNum );
	int				i;

	if ( !cgs.pangea || !id ) {
		return;
	}
	CG_PangeaRegisterCommon();
	s = &pgSlots[weaponNum];
	if ( !s->registered ) {
		s->registered = qtrue;
		if ( weaponNum != WP_GAUNTLET ) {
			s->model = trap_R_RegisterModel( va( "models/weapons2/%s/%s.md3", id, id ) );
			for ( i = 0 ; i < 4 ; i++ ) {
				s->paint[i] = trap_R_RegisterSkin( va( "models/weapons2/%s/%s_paint%i.skin", id, id, i + 1 ) );
			}
		}
		for ( i = 0 ; i < 3 ; i++ ) {
			s->pose[i] = trap_R_RegisterModel( va( "models/hands/%s/%s.md3", pgBuildNames[i], CG_PangeaPoseName( weaponNum ) ) );
		}
		switch ( weaponNum ) {
		case WP_GRENADE_LAUNCHER:
			s->swing = pg.slingRelease;
			s->altSound = pg.throwSound;
			break;
		case WP_ROCKET_LAUNCHER:
			s->swing = pg.bowRelease;
			s->altSound = pg.bowRelease;
			break;
		case WP_RAILGUN:
			s->swing = 0;
			s->altSound = pg.slam;
			break;
		case WP_SHOTGUN:
			s->swing = trap_S_RegisterSound( "sound/weapons/melee/fstatck.wav", qfalse );
			s->altSound = pg.throwSound;
			break;
		default:
			s->swing = trap_S_RegisterSound( "sound/weapons/melee/fstatck.wav", qfalse );
			s->altSound = s->swing;
			break;
		}
	}

	wi->weaponModel = s->model;
	wi->handsModel = s->pose[1];
	wi->barrelModel = 0;
	wi->flashModel = 0;
	wi->flashDlight = 0;
	wi->missileModel = 0;
	wi->missileSound = 0;
	wi->missileTrailFunc = NULL;
	wi->missileDlight = 0;
	wi->ejectBrassFunc = NULL;
	wi->readySound = 0;
	wi->firingSound = 0;
	memset( wi->flashSound, 0, sizeof( wi->flashSound ) );
	wi->flashSound[0] = s->swing;
	wi->weaponIcon = trap_R_RegisterShader( va( "icons/iconw_%s", id ) );
	wi->ammoIcon = wi->weaponIcon;
	if ( weaponNum == WP_GAUNTLET ) {
		wi->weaponModel = 0;
	}
}

/* "pr" of the player configstring */
void CG_PangeaClientInfo( clientInfo_t *ci, const char *configstring ) {
	Q_strncpyz( ci->pangeaRace, Info_ValueForKey( configstring, "pr" ), sizeof( ci->pangeaRace ) );
}

/*
Hands skins of the local player: by people, fists wraps by painting.
*/
static void CG_PangeaLocalHands( void ) {
	const char	*race = cgs.clientinfo[ cg.clientNum ].pangeaRace;
	int			paint = CG_PangeaPaint( cg.clientNum ) + 1;

	if ( !CG_PangeaKnownRace( race ) ) {
		race = "human";
	}
	if ( pg.handSkin && !Q_stricmp( race, pg.race ) ) {
		return;
	}
	Q_strncpyz( pg.race, race, sizeof( pg.race ) );
	pg.build = CG_PangeaBuild( race );
	pg.handSkin = trap_R_RegisterSkin( va( "models/hands/skin/%s.skin", race ) );
	pg.fistSkin = trap_R_RegisterSkin( va( "models/hands/skin/%s_fists%i.skin", race, paint ) );
}

/* EV_FIRE_WEAPON / EV_PANGEA_ALT of the local player */
static void CG_PangeaSwing( int weapon, qboolean alt ) {
	pgSwingTime = cg.time;
	pgSwingWeapon = weapon;
	pgSwingAlt = alt;
}

void CG_PangeaFireWeapon( centity_t *cent ) {
	if ( cent->currentState.number == cg.snap->ps.clientNum ) {
		CG_PangeaSwing( cent->currentState.weapon, qfalse );
	}
}

/*
EV_PANGEA_ALT: the secondary ability (sound, own swing, the slam's dust ring).
*/
void CG_PangeaAltEvent( centity_t *cent, int weapon ) {
	pangeaSlot_t	*s;

	if ( weapon < WP_GAUNTLET || weapon > WP_RAILGUN ) {
		return;
	}
	CG_RegisterWeapon( weapon );
	s = &pgSlots[weapon];
	if ( s->altSound ) {
		trap_S_StartSound( NULL, cent->currentState.number, CHAN_WEAPON, s->altSound );
	}
	if ( cent->currentState.number == cg.snap->ps.clientNum ) {
		CG_PangeaSwing( weapon, qtrue );
	}
	if ( weapon == WP_RAILGUN ) {
		// «удар о землю»: a ring of dust round the feet
		int i;
		for ( i = 0 ; i < 12 ; i++ ) {
			vec3_t	org, vel;
			float	a = i * ( 2 * M_PI / 12 );

			VectorCopy( cent->lerpOrigin, org );
			org[2] -= 20;
			vel[0] = cos( a ) * 160;
			vel[1] = sin( a ) * 160;
			vel[2] = 20;
			CG_SmokePuff( org, vel, 18, 0.55f, 0.45f, 0.32f, 0.8f, 700, cg.time, 0, 0, cgs.media.smokePuffShader );
		}
	}
}

/*
Procedural motion of the first-person hands: offsets along the view axes
(forward, right, up) and angle deltas, by the time since the own swing.
*/
static void CG_PangeaViewMotion( const playerState_t *ps, vec3_t offset, vec3_t dangles ) {
	const pangeaAbility_t	*a;
	float					t, s;
	int						dur;

	VectorClear( offset );
	VectorClear( dangles );

	if ( ps->weapon == WP_RAILGUN && ( ps->generic1 & PSTAT_BLOCKING ) ) {
		// the shield comes up in front of the face
		offset[0] = 2;
		offset[1] = 6;
		offset[2] = 3;
		dangles[YAW] = -8;
		return;
	}
	if ( !pgSwingTime || pgSwingWeapon != ps->weapon ) {
		return;
	}
	a = BG_PangeaAbility( pgSwingWeapon, pgSwingAlt, cgs.pangea );
	dur = a && a->refire > 0 ? a->refire : 400;
	if ( dur > 700 ) {
		dur = 700;		// the motion is quicker than the recovery
	}
	t = (float)( cg.time - pgSwingTime ) / dur;
	if ( t < 0 || t >= 1 ) {
		return;
	}
	s = sin( t * M_PI );

	switch ( pgSwingWeapon ) {
	case WP_GAUNTLET:
		if ( pgSwingAlt ) {
			offset[2] = -10 * s;		// kick / headbutt: the hands drop, the view lunges
			offset[0] = 6 * s;
		} else {
			offset[0] = 12 * s;			// jab
			offset[1] = ( ( pgSwingTime / 100 ) & 1 ? 3 : -3 ) * s;
		}
		break;
	case WP_MACHINEGUN:
		if ( pgSwingAlt ) {
			dangles[PITCH] = -40 + 80 * t;	// overhead: from above the head down
			offset[2] = 6 * s;
		} else {
			dangles[YAW] = 35 - 75 * t;		// horizontal swing right to left
			offset[0] = 6 * s;
		}
		break;
	case WP_SHOTGUN:
	case WP_LIGHTNING:
		if ( pgSwingAlt ) {
			offset[2] = 8 * s;				// throw over the shoulder
			dangles[PITCH] = -25 * s;
			offset[0] = 10 * s;
		} else {
			offset[0] = 16 * s;				// thrust
		}
		break;
	case WP_GRENADE_LAUNCHER:
		dangles[ROLL] = 360 * t * ( pgSwingAlt ? 1 : 2 );		// the sling spins
		offset[2] = 4 * s;
		break;
	case WP_ROCKET_LAUNCHER:
		offset[0] = -4 * s;					// recoil of the string
		dangles[PITCH] = pgSwingAlt ? -10 * s : -2 * s;
		break;
	case WP_RAILGUN:
		offset[2] = -12 * s;				// the shield hits the ground
		break;
	}
}

static void CG_PangeaAddItem( refEntity_t *hands, qhandle_t model, qhandle_t skin, char *tag ) {
	refEntity_t item;

	if ( !model ) {
		return;
	}
	memset( &item, 0, sizeof( item ) );
	item.hModel = model;
	item.customSkin = skin;
	item.renderfx = hands->renderfx;
	VectorCopy( hands->lightingOrigin, item.lightingOrigin );
	CG_PositionEntityOnTag( &item, hands, hands->hModel, tag );
	trap_R_AddRefEntityToScene( &item );
}

/*
Replaces CG_AddViewWeapon in a tier-0 arena: hands of the player's people in the
pose of the slot, the weapon on tag_weapon / tag_weapon_l.
*/
void CG_PangeaAddViewWeapon( playerState_t *ps ) {
	refEntity_t		hands;
	pangeaSlot_t	*s;
	vec3_t			origin, angles, offset, dangles;
	int				weapon = ps->weapon;
	int				paint = CG_PangeaPaint( ps->clientNum );
	qboolean		empty;

	if ( weapon < WP_GAUNTLET || weapon > WP_RAILGUN || ps->stats[STAT_HEALTH] <= 0 ) {
		return;
	}
	CG_RegisterWeapon( weapon );
	CG_PangeaLocalHands();
	s = &pgSlots[weapon];

	// thrown spear / brand: only the empty fist is left
	empty = ( weapon == WP_SHOTGUN && ps->ammo[WP_SHOTGUN] <= 0 ) ||
		( weapon == WP_LIGHTNING && ( ps->ammo[WP_LIGHTNING] <= 0 || ( ps->generic1 & PSTAT_TORCH_OUT ) ) );

	memset( &hands, 0, sizeof( hands ) );
	VectorCopy( cg.refdef.vieworg, origin );
	VectorCopy( cg.refdefViewAngles, angles );
	// a bit of bob: the same feel as the stock gun
	angles[ROLL] += cg.xyspeed * cg.bobfracsin * 0.004 * ( cg.bobcycle & 1 ? -1 : 1 );
	angles[PITCH] += cg.xyspeed * cg.bobfracsin * 0.004;
	origin[2] += sin( cg.time * 0.001 ) * 0.3;

	CG_PangeaViewMotion( ps, offset, dangles );
	VectorAdd( angles, dangles, angles );
	AnglesToAxis( angles, hands.axis );
	VectorMA( origin, offset[0], cg.refdef.viewaxis[0], origin );
	VectorMA( origin, -offset[1], cg.refdef.viewaxis[1], origin );
	VectorMA( origin, offset[2], cg.refdef.viewaxis[2], origin );
	VectorCopy( origin, hands.origin );
	VectorCopy( origin, hands.lightingOrigin );
	hands.renderfx = RF_DEPTHHACK | RF_FIRST_PERSON | RF_MINLIGHT | RF_LIGHTING_ORIGIN;

	if ( weapon == WP_GAUNTLET || empty ) {
		hands.hModel = pg.fistPose[pg.build];
		hands.customSkin = pg.fistSkin;
	} else {
		hands.hModel = s->pose[pg.build];
		hands.customSkin = pg.handSkin;
	}
	if ( !hands.hModel ) {
		return;
	}
	trap_R_AddRefEntityToScene( &hands );
	if ( weapon == WP_GAUNTLET || empty ) {
		return;
	}

	switch ( weapon ) {
	case WP_ROCKET_LAUNCHER:
		CG_PangeaAddItem( &hands, s->model, s->paint[paint], "tag_weapon_l" );
		if ( ps->ammo[WP_ROCKET_LAUNCHER] > 0 && ( !pgSwingTime || cg.time - pgSwingTime > 350 ) ) {
			CG_PangeaAddItem( &hands, pg.arrow, 0, "tag_weapon" );
		}
		break;
	case WP_GRENADE_LAUNCHER:
		CG_PangeaAddItem( &hands, s->model, s->paint[paint], "tag_weapon" );
		if ( ps->ammo[WP_GRENADE_LAUNCHER] > 0 ) {
			CG_PangeaAddItem( &hands, pg.stones[0], 0, "tag_weapon_l" );
		}
		break;
	case WP_RAILGUN:
		CG_PangeaAddItem( &hands, s->model, s->paint[paint], "tag_weapon_l" );
		break;
	default:
		CG_PangeaAddItem( &hands, s->model, s->paint[paint], "tag_weapon" );
		break;
	}

	if ( weapon == WP_LIGHTNING ) {
		vec3_t light;
		VectorMA( cg.refdef.vieworg, 24, cg.refdef.viewaxis[0], light );
		trap_R_AddLightToScene( light, 180 + ( rand() & 31 ), 1.0f, 0.6f, 0.25f );
	}
}

/*
Replaces CG_AddPlayerWeapon for other players (and the own body in third person).
qtrue = drawn here.
*/
qboolean CG_PangeaAddPlayerWeapon( refEntity_t *parent, playerState_t *ps, centity_t *cent ) {
	refEntity_t		gun;
	pangeaSlot_t	*s;
	int				weapon = cent->currentState.weapon;

	if ( !cgs.pangea || weapon < WP_GAUNTLET || weapon > WP_RAILGUN ) {
		return qfalse;
	}
	CG_RegisterWeapon( weapon );
	s = &pgSlots[weapon];
	if ( !s->model || ( weapon == WP_LIGHTNING && ( cent->currentState.generic1 & PSTAT_TORCH_OUT ) ) ) {
		return qtrue;
	}
	memset( &gun, 0, sizeof( gun ) );
	VectorCopy( parent->lightingOrigin, gun.lightingOrigin );
	gun.shadowPlane = parent->shadowPlane;
	gun.renderfx = parent->renderfx;
	gun.hModel = s->model;
	gun.customSkin = s->paint[ CG_PangeaPaint( cent->currentState.clientNum ) ];
	CG_PositionEntityOnTag( &gun, parent, parent->hModel, "tag_weapon" );
	trap_R_AddRefEntityToScene( &gun );

	if ( weapon == WP_LIGHTNING ) {
		trap_R_AddLightToScene( gun.origin, 160 + ( rand() & 31 ), 1.0f, 0.6f, 0.25f );
		trap_S_AddLoopingSound( cent->currentState.number, cent->lerpOrigin, vec3_origin, pg.fire );
	}
	return qtrue;
}

/*
Burning, bola on the legs, stun stars: called from CG_Player with the legs entity.
*/
void CG_PangeaPlayerEffects( centity_t *cent, refEntity_t *legs ) {
	int flags = cent->currentState.generic1;

	if ( !cgs.pangea || !flags ) {
		return;
	}
	CG_PangeaRegisterCommon();
	if ( flags & PSTAT_BURNING ) {
		refEntity_t	fl;
		int			i;

		for ( i = 0 ; i < 3 ; i++ ) {
			memset( &fl, 0, sizeof( fl ) );
			fl.reType = RT_SPRITE;
			fl.customShader = pg.flameShader;
			fl.radius = 14 + ( ( cg.time / 90 + i * 7 ) % 5 );
			VectorCopy( cent->lerpOrigin, fl.origin );
			fl.origin[0] += ( i - 1 ) * 8;
			fl.origin[2] += -8 + i * 14;
			fl.shaderRGBA[0] = fl.shaderRGBA[1] = fl.shaderRGBA[2] = fl.shaderRGBA[3] = 255;
			trap_R_AddRefEntityToScene( &fl );
		}
		trap_R_AddLightToScene( cent->lerpOrigin, 150 + ( rand() & 31 ), 1.0f, 0.55f, 0.2f );
	}
	if ( ( flags & PSTAT_ENTANGLED ) && pg.bola ) {
		refEntity_t	b;
		vec3_t		angles;

		memset( &b, 0, sizeof( b ) );
		b.hModel = pg.bola;
		VectorCopy( cent->lerpOrigin, b.origin );
		b.origin[2] -= 14;
		VectorSet( angles, 0, cg.time * 0.05f, 0 );
		AnglesToAxis( angles, b.axis );
		VectorCopy( legs->lightingOrigin, b.lightingOrigin );
		b.renderfx = legs->renderfx & ~RF_THIRD_PERSON;
		trap_R_AddRefEntityToScene( &b );
	}
	if ( flags & PSTAT_STUNNED ) {
		int i;
		for ( i = 0 ; i < 3 ; i++ ) {
			vec3_t	org;
			float	a = cg.time * 0.006f + i * ( 2 * M_PI / 3 );

			VectorCopy( cent->lerpOrigin, org );
			org[0] += cos( a ) * 12;
			org[1] += sin( a ) * 12;
			org[2] += 40;
			CG_SmokePuff( org, vec3_origin, 3, 1.0f, 0.9f, 0.5f, 1.0f, 60, cg.time, 0, 0, cgs.media.smokePuffShader );
		}
	}
}

static void CG_PangeaAxisFromDir( const vec3_t dir, vec3_t axis[3] ) {
	VectorCopy( dir, axis[0] );
	if ( VectorNormalize( axis[0] ) == 0 ) {
		VectorSet( axis[0], 1, 0, 0 );
	}
	PerpendicularVector( axis[1], axis[0] );
	CrossProduct( axis[0], axis[1], axis[2] );
}

/*
Missiles with es->generic1 = PK_*. qtrue = drawn here.
*/
qboolean CG_PangeaMissile( centity_t *cent ) {
	entityState_t	*s1 = &cent->currentState;
	refEntity_t		ent;
	vec3_t			vel, angles;

	if ( !cgs.pangea || s1->generic1 <= PK_NONE || s1->generic1 >= PK_NUM ) {
		return qfalse;
	}
	CG_PangeaRegisterCommon();
	memset( &ent, 0, sizeof( ent ) );
	VectorCopy( cent->lerpOrigin, ent.origin );
	VectorCopy( cent->lerpOrigin, ent.oldorigin );
	BG_EvaluateTrajectoryDelta( &s1->pos, cg.time, vel );

	switch ( s1->generic1 ) {
	case PK_STONE:
		ent.hModel = pg.stones[ s1->number & 3 ];
		VectorSet( angles, cg.time * 0.7f, cg.time * 0.4f, 0 );
		AnglesToAxis( angles, ent.axis );
		break;
	case PK_BOLA:
		ent.hModel = pg.bola;
		CG_PangeaAxisFromDir( vel, ent.axis );
		VectorSet( angles, 0, cg.time * 1.2f, 0 );
		AnglesToAxis( angles, ent.axis );		// spins flat like a star
		break;
	case PK_ARROW:
		ent.hModel = pg.arrow;
		CG_PangeaAxisFromDir( vel, ent.axis );
		break;
	case PK_ARROW_FIRE:
		ent.hModel = pg.arrowFire;
		CG_PangeaAxisFromDir( vel, ent.axis );
		trap_R_AddLightToScene( ent.origin, 120, 1.0f, 0.55f, 0.2f );
		break;
	case PK_SPEAR:
		ent.hModel = pg.spear;
		CG_PangeaAxisFromDir( vel, ent.axis );
		break;
	case PK_BRAND:
		ent.hModel = pg.brand;
		VectorSet( angles, cg.time * 0.5f, 0, cg.time * 0.3f );
		AnglesToAxis( angles, ent.axis );
		trap_R_AddLightToScene( ent.origin, 140, 1.0f, 0.55f, 0.2f );
		break;
	default:
		return qtrue;
	}
	if ( ent.hModel ) {
		trap_R_AddRefEntityToScene( &ent );
	}
	return qtrue;
}

/*
ET_GENERAL with es->generic1: the fire patch (the lying spear has a model index
and is drawn by CG_General). qtrue = drawn here.
*/
qboolean CG_PangeaGeneral( centity_t *cent ) {
	entityState_t	*s1 = &cent->currentState;
	refEntity_t		fl;
	float			life, fade;
	int				i;

	if ( !cgs.pangea || s1->generic1 != PK_FIRE ) {
		return qfalse;
	}
	CG_PangeaRegisterCommon();
	life = (float)( cg.time - s1->time ) / PANGEA_FIRE_TIME;
	fade = life < 0.8f ? 1.0f : ( 1.0f - life ) * 5;
	if ( fade <= 0 ) {
		return qtrue;
	}
	for ( i = 0 ; i < 7 ; i++ ) {
		float a = i * ( 2 * M_PI / 7 ) + s1->number;
		float r = i ? PANGEA_FIRE_RADIUS * 0.55f : 0;

		memset( &fl, 0, sizeof( fl ) );
		fl.reType = RT_SPRITE;
		fl.customShader = pg.flameShader;
		fl.radius = ( 18 + ( ( cg.time / 80 + i * 3 ) % 6 ) ) * fade;
		VectorCopy( cent->lerpOrigin, fl.origin );
		fl.origin[0] += cos( a ) * r;
		fl.origin[1] += sin( a ) * r;
		fl.origin[2] += fl.radius * 0.8f;
		fl.shaderRGBA[0] = fl.shaderRGBA[1] = fl.shaderRGBA[2] = fl.shaderRGBA[3] = 255;
		trap_R_AddRefEntityToScene( &fl );
	}
	trap_R_AddLightToScene( cent->lerpOrigin, ( 220 + ( rand() & 31 ) ) * fade, 1.0f, 0.55f, 0.2f );
	trap_S_AddLoopingSound( s1->number, cent->lerpOrigin, vec3_origin, pg.fire );
	if ( ( cg.time / 200 ) % 3 == 0 && cent->trailTime + 200 < cg.time ) {
		vec3_t up = { 0, 0, 40 };
		cent->trailTime = cg.time;
		CG_SmokePuff( cent->lerpOrigin, up, 20, 0.15f, 0.12f, 0.1f, 0.5f * fade, 1500, cg.time, 0, 0, cgs.media.smokePuffShader );
	}
	return qtrue;
}

/*
Missile and melee impacts in a tier-0 arena: dust, a «sim-field» spark, a thud.
qtrue = handled (no stock explosions).
*/
qboolean CG_PangeaImpact( int weapon, vec3_t origin, vec3_t dir, int fleshEntity ) {
	vec3_t	vel;

	if ( !cgs.pangea || weapon < WP_GAUNTLET || weapon > WP_RAILGUN ) {
		return qfalse;
	}
	CG_PangeaRegisterCommon();
	VectorScale( dir, 40, vel );
	if ( fleshEntity >= 0 ) {
		CG_Bleed( origin, fleshEntity );
		// the arena's simulation field flashes where the blow lands
		CG_SmokePuff( origin, vec3_origin, 10, 0.6f, 0.8f, 1.0f, 1.0f, 180, cg.time, 0, LEF_PUFF_DONT_SCALE, cgs.media.smokePuffShader );
		trap_S_StartSound( origin, ENTITYNUM_WORLD, CHAN_AUTO, pg.hitFlesh );
	} else {
		CG_SmokePuff( origin, vel, 14, 0.55f, 0.45f, 0.32f, 0.7f, 600, cg.time, 0, 0, cgs.media.smokePuffShader );
		trap_S_StartSound( origin, ENTITYNUM_WORLD, CHAN_AUTO,
			weapon == WP_GRENADE_LAUNCHER ? pg.hitStone : pg.hitWall );
		if ( weapon == WP_LIGHTNING ) {
			CG_ImpactMark( cgs.media.burnMarkShader, origin, dir, random() * 360, 1, 1, 1, 1, qfalse, 40, qfalse );
		}
	}
	return qtrue;
}

/*
HUD: the secondary ability of the slot in hand — ready or the seconds left.
*/
void CG_PangeaDrawHud( void ) {
	const playerState_t		*ps = &cg.snap->ps;
	const pangeaAbility_t	*a;
	int						cd;
	const char				*s;
	vec4_t					color;

	if ( !cgs.pangea || ps->persistant[PERS_TEAM] == TEAM_SPECTATOR || ps->stats[STAT_HEALTH] <= 0 ) {
		return;
	}
	if ( ps->weapon < WP_GAUNTLET || ps->weapon > WP_RAILGUN ) {
		return;
	}
	a = BG_PangeaAbility( ps->weapon, qtrue, cgs.pangea );
	if ( !a ) {
		return;
	}
	cd = ps->stats[ STAT_PANGEA_CD1 + ps->weapon - WP_GAUNTLET ];
	if ( cd > 0 ) {
		s = va( "%s %i", a->id, ( cd + 999 ) / 1000 );
		Vector4Set( color, 0.8f, 0.6f, 0.4f, 0.8f );
	} else {
		s = va( "%s [MOUSE2/F]", a->id );
		Vector4Set( color, 0.95f, 0.8f, 0.5f, 1.0f );
	}
	CG_DrawStringExt( 320 - CG_DrawStrlen( s ) * 4, 412, s, color, qtrue, qtrue, 8, 10, 0 );

	if ( ps->generic1 & ( PSTAT_ENTANGLED | PSTAT_STUNNED | PSTAT_BURNING ) ) {
		s = ( ps->generic1 & PSTAT_BURNING ) ? "BURNING" : ( ps->generic1 & PSTAT_STUNNED ) ? "STUNNED" : "TANGLED";
		Vector4Set( color, 1.0f, 0.5f, 0.25f, 1.0f );
		CG_DrawStringExt( 320 - CG_DrawStrlen( s ) * 4, 398, s, color, qtrue, qtrue, 8, 10, 0 );
	}
}

/*
Arena controls: the secondary ability on the right mouse button and F.
*/
void CG_PangeaInit( void ) {
	if ( !cgs.pangea ) {
		return;
	}
	trap_SendConsoleCommand( "bind MOUSE2 +button12\nbind f +button12\n" );
}
