/*
===========================================================================
Pangea Arena match rules. Copyright (C) 2026 Pangea contributors.

This file is part of Pangea Arena, a fork of ioquake3, and is distributed
under the terms of the GNU General Public License version 2 or later
(see COPYING.txt).
===========================================================================

Rules are plain cvars set by the match manager on the ioq3ded command line:

  g_pangea_tickets   "t1,t2,..."  only clients with userinfo pangea_ticket in the list
  g_pangea_arsenal   full | rail | rocket | melee   «симулятор»: stock OpenArena weapons
                     honor | slaughter              tier-0 abilities (bg_pangea.h): дуэль чести / бойня
  g_pangea_races     "key=race,..."  people of each entrant, key = ticket or the bot's name;
                                     shown as "pr" in the player configstring (hands, skin)
  g_pangea_instagib  0/1          railgun hits deal 1000
  g_pangea_powerups  0/1          spawn quad/haste/regen/invis/flight/battlesuit
  g_pangea_items     0/1          spawn armor and health
  g_pangea_bots      0..3         bots allowed in (the manager issues addbot itself)
  g_pangea_autoexit  0/1          quit the server 5 s after the match result is logged
  g_pangea_overtime  seconds      (120) a tie at the timelimit plays sudden death this long,
                                  then ends as a draw (0 = sudden death without end)

"Pangea mode" = g_pangea_tickets is not empty: votes are off, team/follow are
spectator-only.
*/

#include "g_local.h"

vmCvar_t	g_pangea_tickets;
vmCvar_t	g_pangea_arsenal;
vmCvar_t	g_pangea_instagib;
vmCvar_t	g_pangea_powerups;
vmCvar_t	g_pangea_items;
vmCvar_t	g_pangea_bots;
vmCvar_t	g_pangea_autoexit;
vmCvar_t	g_pangea_overtime;

static int	pangeaQuitTime;

// ticket of each client slot ("" = none, "bot" for bots)
static char	pangeaTickets[MAX_CLIENTS][64];
// people of each client slot ("" = unknown: the client draws human hands)
static char	pangeaRaces[MAX_CLIENTS][24];

// "Infinite" ammo for rail/rocket arsenals. Not -1: bot AI treats -1 as empty.
#define PANGEA_AMMO	99

qboolean Pangea_Active( void ) {
	return g_pangea_tickets.string[0] != '\0';
}

pangeaArsenal_t Pangea_Arsenal( void ) {
	if ( !Q_stricmp( g_pangea_arsenal.string, "rail" ) ) {
		return PANGEA_ARSENAL_RAIL;
	}
	if ( !Q_stricmp( g_pangea_arsenal.string, "rocket" ) ) {
		return PANGEA_ARSENAL_ROCKET;
	}
	if ( !Q_stricmp( g_pangea_arsenal.string, "melee" ) ) {
		return PANGEA_ARSENAL_MELEE;
	}
	if ( !Q_stricmp( g_pangea_arsenal.string, "honor" ) ) {
		return PANGEA_ARSENAL_HONOR;
	}
	if ( !Q_stricmp( g_pangea_arsenal.string, "slaughter" ) ) {
		return PANGEA_ARSENAL_SLAUGHTER;
	}
	return PANGEA_ARSENAL_FULL;
}

int Pangea_Mode( void ) {
	switch ( Pangea_Arsenal() ) {
	case PANGEA_ARSENAL_HONOR:		return PANGEA_HONOR;
	case PANGEA_ARSENAL_SLAUGHTER:	return PANGEA_SLAUGHTER;
	default:						return PANGEA_SIM;
	}
}

/*
Is <ticket> one of the comma separated entries of g_pangea_tickets?
Whitespace around entries is ignored. Comparison is exact (case sensitive).
*/
static qboolean Pangea_TicketListed( const char *ticket ) {
	const char	*p = g_pangea_tickets.string;
	int			len = strlen( ticket );

	if ( !len ) {
		return qfalse;
	}
	while ( *p ) {
		const char	*start, *end;

		while ( *p == ' ' || *p == ',' ) {
			p++;
		}
		start = p;
		while ( *p && *p != ',' ) {
			p++;
		}
		end = p;
		while ( end > start && end[-1] == ' ' ) {
			end--;
		}
		if ( end - start == len && !Q_strncmp( start, ticket, len ) ) {
			return qtrue;
		}
	}
	return qfalse;
}

/*
Called from ClientConnect before the client slot is reset.
Returns NULL to accept or a reject message.
*/
const char *Pangea_CheckConnect( int clientNum, const char *userinfo, qboolean isBot ) {
	const char	*ticket;
	int			i;

	if ( !Pangea_Active() ) {
		return NULL;
	}
	if ( isBot ) {
		return g_pangea_bots.integer > 0 ? NULL : "Это не ваша арена";
	}
	ticket = Info_ValueForKey( userinfo, "pangea_ticket" );
	if ( !Pangea_TicketListed( ticket ) ) {
		return "Это не ваша арена";
	}
	// the same ticket must not be used by two connected clients at once
	for ( i = 0 ; i < level.maxclients ; i++ ) {
		gclient_t *cl = &level.clients[i];
		if ( i == clientNum || cl->pers.connected == CON_DISCONNECTED ) {
			continue;
		}
		if ( !strcmp( pangeaTickets[i], ticket ) ) {
			return "Этот билет уже на арене";
		}
	}
	return NULL;
}

/*
The people of <key> (a ticket or a bot name) from g_pangea_races "key=race,key=race".
Only [a-z_] survive in the race (it goes into a configstring and a file name).
*/
static void Pangea_LookupRace( const char *key, char *out, int size ) {
	char		list[MAX_STRING_CHARS];
	const char	*p = list;
	int			len = strlen( key );

	out[0] = '\0';
	if ( !len ) {
		return;
	}
	trap_Cvar_VariableStringBuffer( "g_pangea_races", list, sizeof( list ) );
	while ( *p ) {
		const char	*start, *eq;

		while ( *p == ' ' || *p == ',' ) {
			p++;
		}
		start = p;
		while ( *p && *p != ',' ) {
			p++;
		}
		eq = strchr( start, '=' );
		if ( eq && eq < p && eq - start == len && !Q_stricmpn( start, key, len ) ) {
			int n = 0;
			for ( eq++ ; eq < p && n < size - 1 ; eq++ ) {
				char c = *eq;
				if ( c >= 'A' && c <= 'Z' ) {
					c += 'a' - 'A';
				}
				if ( ( c >= 'a' && c <= 'z' ) || c == '_' ) {
					out[n++] = c;
				}
			}
			out[n] = '\0';
			return;
		}
	}
}

const char *Pangea_ClientRace( int clientNum ) {
	if ( clientNum < 0 || clientNum >= MAX_CLIENTS || !Pangea_Active() ) {
		return "";
	}
	return pangeaRaces[clientNum];
}

/*
Called from ClientConnect after the client slot was reset and accepted.
*/
void Pangea_ClientConnected( int clientNum, const char *userinfo, qboolean isBot ) {
	if ( !Pangea_Active() ) {
		return;
	}
	Q_strncpyz( pangeaTickets[clientNum], isBot ? "bot" : Info_ValueForKey( userinfo, "pangea_ticket" ),
		sizeof( pangeaTickets[clientNum] ) );
	Pangea_LookupRace( isBot ? Info_ValueForKey( userinfo, "name" ) : pangeaTickets[clientNum],
		pangeaRaces[clientNum], sizeof( pangeaRaces[clientNum] ) );
	G_LogPrintf( "Pangea: ticket %s client %i\n", pangeaTickets[clientNum], clientNum );
	// The gateway's UDP socket of this browser: the manager kicks the slot when its
	// WebSocket closes (a closed arena tab would otherwise linger until sv_timeout).
	if ( !isBot ) {
		G_LogPrintf( "Pangea: addr client %i %s\n", clientNum, Info_ValueForKey( userinfo, "pangea_addr" ) );
	}
}

/*
Called from ClientSpawn instead of the stock "machinegun + gauntlet" loadout.
*/
void Pangea_GiveArsenal( gclient_t *client ) {
	int i;

	for ( i = 0 ; i < MAX_WEAPONS ; i++ ) {
		client->ps.ammo[i] = 0;
	}
	client->ps.stats[STAT_WEAPONS] = ( 1 << WP_GAUNTLET );
	client->ps.ammo[WP_GAUNTLET] = -1;
	client->ps.ammo[WP_GRAPPLING_HOOK] = -1;

	client->pangeaBurnUntil = client->pangeaBurnNext = 0;
	client->pangeaBurnBy = -1;
	client->pangeaEntangleUntil = client->pangeaStunUntil = 0;
	client->pangeaTorchBack = client->pangeaSpearBack = 0;
	client->ps.generic1 = 0;

	if ( Pangea_Mode() != PANGEA_SIM ) {
		int mode = Pangea_Mode();

		client->ps.stats[STAT_WEAPONS] = 0;
		client->ps.ammo[WP_GRAPPLING_HOOK] = 0;
		for ( i = WP_GAUNTLET ; i <= WP_RAILGUN ; i++ ) {
			client->ps.stats[STAT_PANGEA_CD1 + i - WP_GAUNTLET] = 0;
			if ( !BG_PangeaSlotAllowed( i, mode ) ) {
				continue;
			}
			client->ps.stats[STAT_WEAPONS] |= ( 1 << i );
			switch ( i ) {
			case WP_SHOTGUN:			// the spear and the torch: one in the hand
			case WP_LIGHTNING:
				client->ps.ammo[i] = 1;
				break;
			case WP_GRENADE_LAUNCHER:
				client->ps.ammo[i] = PANGEA_STONES_START;
				break;
			case WP_ROCKET_LAUNCHER:
				client->ps.ammo[i] = PANGEA_ARROWS_START;
				break;
			default:
				client->ps.ammo[i] = PANGEA_MELEE_AMMO;
				break;
			}
		}
		return;
	}

	switch ( Pangea_Arsenal() ) {
	case PANGEA_ARSENAL_RAIL:
		client->ps.stats[STAT_WEAPONS] |= ( 1 << WP_RAILGUN );
		client->ps.ammo[WP_RAILGUN] = PANGEA_AMMO;	// refilled every frame
		break;
	case PANGEA_ARSENAL_ROCKET:
		client->ps.stats[STAT_WEAPONS] |= ( 1 << WP_ROCKET_LAUNCHER );
		client->ps.ammo[WP_ROCKET_LAUNCHER] = PANGEA_AMMO;
		break;
	case PANGEA_ARSENAL_MELEE:
		break;
	default:
		client->ps.stats[STAT_WEAPONS] |= ( 1 << WP_MACHINEGUN );
		client->ps.ammo[WP_MACHINEGUN] = g_gametype.integer == GT_TEAM ? 50 : 100;
		break;
	}
}

/*
Called from G_CallSpawn for map items. qfalse = do not spawn.
*/
qboolean Pangea_ItemAllowed( const gitem_t *item ) {
	if ( !Q_strncmp( item->classname, "pangea_", 7 ) ) {
		return Pangea_Mode() != PANGEA_SIM;
	}
	switch ( item->giType ) {
	case IT_WEAPON:
	case IT_AMMO:
		return Pangea_Arsenal() == PANGEA_ARSENAL_FULL;
	case IT_POWERUP:
		return g_pangea_powerups.integer != 0;
	case IT_ARMOR:
	case IT_HEALTH:
		return g_pangea_items.integer != 0;
	default:
		return qtrue;
	}
}

int Pangea_ModifyDamage( gentity_t *targ, gentity_t *inflictor, int damage, int mod ) {
	if ( g_pangea_instagib.integer && mod == MOD_RAILGUN ) {
		return 1000;
	}
	// the shield takes the blow when it is up and the blow comes from the front
	if ( Pangea_Mode() != PANGEA_SIM && targ->client && inflictor && inflictor != targ &&
		( targ->client->ps.generic1 & PSTAT_BLOCKING ) && mod != MOD_PANGEA_BURN ) {
		vec3_t	facing, from;

		AngleVectors( targ->client->ps.viewangles, facing, NULL, NULL );
		facing[2] = 0;
		VectorNormalize( facing );
		VectorSubtract( inflictor->r.currentOrigin, targ->r.currentOrigin, from );
		from[2] = 0;
		if ( VectorNormalize( from ) > 0 && DotProduct( facing, from ) > PANGEA_BLOCK_DOT ) {
			damage = damage * PANGEA_BLOCK_FACTOR;
			if ( damage < 1 ) {
				damage = 1;
			}
			G_AddEvent( targ, EV_GRENADE_BOUNCE, 0 );		// thud of the blow on the shield
		}
	}
	return damage;
}

/*
Client command filter. qtrue = the command is blocked (a message was sent).
*/
qboolean Pangea_BlockCommand( gentity_t *ent, const char *cmd ) {
	if ( !Pangea_Active() ) {
		return qfalse;
	}
	if ( !Q_stricmp( cmd, "callvote" ) || !Q_stricmp( cmd, "callteamvote" ) ) {
		trap_SendServerCommand( ent - g_entities, "print \"Голосования на арене отключены.\n\"" );
		return qtrue;
	}
	if ( !Q_stricmp( cmd, "team" ) || !Q_stricmp( cmd, "follow" ) ||
		 !Q_stricmp( cmd, "follownext" ) || !Q_stricmp( cmd, "followprev" ) ) {
		if ( ent->client->sess.sessionTeam != TEAM_SPECTATOR ) {
			trap_SendServerCommand( ent - g_entities, "print \"Только для зрителей.\n\"" );
			return qtrue;
		}
	}
	return qfalse;
}

/*
A tie at the timelimit: qtrue once the sudden death has lasted g_pangea_overtime
seconds - the match ends as a draw (idle players at 0:0 would wait forever).
*/
qboolean Pangea_OvertimeOver( void ) {
	int limit;

	if ( g_pangea_overtime.integer <= 0 || g_timelimit.integer <= 0 || level.warmupTime ) {
		return qfalse;
	}
	if ( g_timelimit.integer > ( INT_MAX - g_pangea_overtime.integer * 1000 ) / 60000 ) {
		return qfalse;
	}
	limit = g_timelimit.integer * 60000 + g_pangea_overtime.integer * 1000;
	return level.time - level.startTime >= limit;
}

/*
Called at the end of LogExit, after the "Exit:" and "score:" lines.
*/
void Pangea_MatchLogged( void ) {
	if ( g_pangea_autoexit.integer ) {
		pangeaQuitTime = level.time + 5000;
	}
}

/*
Called every server frame (G_RunFrame) and from G_UpdateCvars.
*/
void Pangea_RunFrame( void ) {
	pangeaArsenal_t	arsenal = Pangea_Arsenal();
	int				i;

	if ( arsenal == PANGEA_ARSENAL_RAIL || arsenal == PANGEA_ARSENAL_ROCKET ) {
		int weapon = arsenal == PANGEA_ARSENAL_RAIL ? WP_RAILGUN : WP_ROCKET_LAUNCHER;
		for ( i = 0 ; i < level.maxclients ; i++ ) {
			gclient_t *cl = &level.clients[i];
			if ( cl->pers.connected == CON_CONNECTED && ( cl->ps.stats[STAT_WEAPONS] & ( 1 << weapon ) ) ) {
				cl->ps.ammo[weapon] = PANGEA_AMMO;
			}
		}
	}
	if ( Pangea_Active() && g_allowVote.integer ) {
		trap_Cvar_Set( "g_allowVote", "0" );
	}
	if ( pangeaQuitTime && level.time >= pangeaQuitTime ) {
		pangeaQuitTime = 0;
		G_LogPrintf( "Pangea: quit\n" );
		trap_SendConsoleCommand( EXEC_APPEND, "quit\n" );
	}
}


/*
===========================================================================
Tier-0 abilities (g_pangea_arsenal honor | slaughter). The table and the
predicted part (cooldowns, ammo, leap) are in bg_pangea.c / bg_pmove.c.
===========================================================================
*/

/*
Arena loadout keeps the spear in hand when a player spawns (the stock code takes
the highest slot, which would be the shield).
*/
void Pangea_SpawnWeapon( gclient_t *client ) {
	if ( Pangea_Mode() == PANGEA_SIM ) {
		return;
	}
	if ( client->ps.stats[STAT_WEAPONS] & ( 1 << WP_SHOTGUN ) ) {
		client->ps.weapon = WP_SHOTGUN;
	} else {
		client->ps.weapon = WP_GAUNTLET;
	}
}

/*
Map weapons and ammo become quivers and stones; NULL = keep the item as it is.
*/
gitem_t *Pangea_ItemReplace( gitem_t *item ) {
	if ( Pangea_Mode() == PANGEA_SIM || ( item->giType != IT_WEAPON && item->giType != IT_AMMO ) ) {
		return NULL;
	}
	switch ( item->giTag ) {
	case WP_GRENADE_LAUNCHER:
	case WP_SHOTGUN:
	case WP_MACHINEGUN:
		return BG_FindItem( "Stones" );
	default:
		return BG_FindItem( "Quiver" );
	}
}

int Pangea_AmmoMax( int weapon ) {
	if ( Pangea_Mode() != PANGEA_SIM ) {
		if ( weapon == WP_ROCKET_LAUNCHER ) {
			return PANGEA_ARROWS_MAX;
		}
		if ( weapon == WP_GRENADE_LAUNCHER ) {
			return PANGEA_STONES_MAX;
		}
	}
	return 200;
}

static void Pangea_Ignite( gentity_t *targ, gentity_t *by, int ms ) {
	gclient_t *c = targ->client;

	if ( !c || targ->health <= 0 || ms <= 0 ) {
		return;
	}
	if ( c->pangeaBurnUntil < level.time + ms ) {
		c->pangeaBurnUntil = level.time + ms;
	}
	if ( c->pangeaBurnNext <= level.time ) {
		c->pangeaBurnNext = level.time + PANGEA_BURN_TICK;
	}
	c->pangeaBurnBy = by ? by->s.number : -1;
}

/*
Burn, bola, stun of an ability that has hit <targ>.
*/
static void Pangea_Afflict( gentity_t *targ, gentity_t *attacker, const pangeaAbility_t *a ) {
	gclient_t *c = targ->client;

	if ( !c || targ->health <= 0 ) {
		return;
	}
	if ( a->flags & PAF_BURN ) {
		Pangea_Ignite( targ, attacker, a->effectTime );
	}
	if ( ( a->flags & PAF_ENTANGLE ) && c->pangeaEntangleUntil < level.time + a->effectTime ) {
		c->pangeaEntangleUntil = level.time + a->effectTime;
	}
	if ( ( a->flags & PAF_STUN ) && c->pangeaStunUntil < level.time + a->effectTime ) {
		c->pangeaStunUntil = level.time + a->effectTime;
	}
}

static void Pangea_Push( gentity_t *targ, const vec3_t dir, float horizontal, float up ) {
	vec3_t d;

	if ( !targ->client || targ->health <= 0 ) {
		return;
	}
	VectorCopy( dir, d );
	d[2] = 0;
	VectorNormalize( d );
	VectorMA( targ->client->ps.velocity, horizontal, d, targ->client->ps.velocity );
	targ->client->ps.velocity[2] += up;
	targ->client->ps.pm_time = 200;
	targ->client->ps.pm_flags |= PMF_TIME_KNOCKBACK;
}

static float Pangea_DamageScale( gentity_t *ent ) {
	return ent->client->ps.powerups[PW_QUAD] ? g_quadfactor.value : 1.0f;
}

/*
Melee strike: one trace straight ahead, or three in a horizontal arc (PAF_ARC).
Each target is hit once.
*/
static void Pangea_Melee( gentity_t *ent, const pangeaAbility_t *a ) {
	static const vec3_t	mins = { -6, -6, -6 }, maxs = { 6, 6, 6 };
	vec3_t		angles, fwd, right, up, muzzle, dir, end;
	int			hit[3];
	int			nhit = 0, ray, rays = ( a->flags & PAF_ARC ) ? 3 : 1;

	VectorCopy( ent->client->ps.viewangles, angles );
	AngleVectors( angles, fwd, right, up );
	CalcMuzzlePoint( ent, fwd, right, up, muzzle );

	for ( ray = 0 ; ray < rays ; ray++ ) {
		trace_t		tr;
		gentity_t	*t;
		vec3_t		a2;
		int			i;
		qboolean	seen = qfalse;

		VectorCopy( angles, a2 );
		if ( rays == 3 ) {
			a2[YAW] += ( ray - 1 ) * 25;
		}
		AngleVectors( a2, dir, NULL, NULL );
		VectorMA( muzzle, a->range, dir, end );
		trap_Trace( &tr, muzzle, mins, maxs, end, ent->s.number, MASK_SHOT );
		if ( tr.entityNum >= ENTITYNUM_MAX_NORMAL ) {
			continue;
		}
		t = &g_entities[tr.entityNum];
		if ( !t->takedamage ) {
			continue;
		}
		for ( i = 0 ; i < nhit ; i++ ) {
			if ( hit[i] == tr.entityNum ) {
				seen = qtrue;
			}
		}
		if ( seen ) {
			continue;
		}
		hit[nhit++] = tr.entityNum;

		if ( t->client ) {
			gentity_t *tent = G_TempEntity( tr.endpos, EV_MISSILE_HIT );
			tent->s.otherEntityNum = t->s.number;
			tent->s.eventParm = DirToByte( tr.plane.normal );
			tent->s.weapon = ent->s.weapon;
			tent->s.generic1 = PK_NONE;
		}
		G_Damage( t, ent, ent, dir, tr.endpos, a->damage * Pangea_DamageScale( ent ), 0, a->mod );
		if ( a->flags & PAF_KNOCK ) {
			Pangea_Push( t, dir, 380, 160 );
		}
		Pangea_Afflict( t, ent, a );
		if ( t->client ) {
			ent->client->accuracy_hits++;
		}
	}
}

static const char *Pangea_KindModel( int kind ) {
	switch ( kind ) {
	case PK_STONE:			return "models/projectiles/proj_stone1.md3";
	case PK_BOLA:			return "models/projectiles/proj_bola.md3";
	case PK_ARROW:			return "models/projectiles/proj_arrow.md3";
	case PK_ARROW_FIRE:		return "models/projectiles/proj_arrow_fire.md3";
	case PK_SPEAR:
	case PK_SPEAR_GROUND:	return "models/weapons2/spear/spear.md3";
	case PK_BRAND:			return "models/projectiles/proj_brand.md3";
	default:				return NULL;
	}
}

static const pangeaAbility_t *Pangea_MissileAbility( gentity_t *missile ) {
	if ( missile->count < 0 || missile->count >= bg_numPangeaAbilities ) {
		return NULL;
	}
	return &bg_pangeaAbilities[missile->count];
}

static void Pangea_BrandLand( gentity_t *brand );

static void Pangea_FireMissile( gentity_t *ent, const pangeaAbility_t *a ) {
	vec3_t		angles, fwd, right, up, muzzle;
	gentity_t	*bolt;

	VectorCopy( ent->client->ps.viewangles, angles );
	if ( a->flags & PAF_LOB ) {
		angles[PITCH] -= 25;
		if ( angles[PITCH] < -89 ) {
			angles[PITCH] = -89;
		}
	}
	AngleVectors( angles, fwd, right, up );
	CalcMuzzlePointOrigin( ent, ent->client->oldOrigin, fwd, right, up, muzzle );

	bolt = G_Spawn();
	bolt->classname = "pangea_missile";
	bolt->s.eType = ET_MISSILE;
	bolt->r.svFlags = SVF_USE_CURRENT_ORIGIN;
	bolt->s.weapon = a->weapon;
	bolt->s.generic1 = a->kind;
	bolt->count = a - bg_pangeaAbilities;
	bolt->r.ownerNum = ent->s.number;
	bolt->parent = ent;
	bolt->damage = a->damage * Pangea_DamageScale( ent );
	bolt->splashDamage = 0;
	bolt->splashRadius = 0;
	bolt->methodOfDeath = a->mod;
	bolt->splashMethodOfDeath = a->mod;
	bolt->clipmask = MASK_SHOT;
	bolt->target_ent = NULL;
	if ( a->flags & PAF_BOUNCE ) {
		bolt->s.eFlags = EF_BOUNCE_HALF;
		bolt->nextthink = level.time + 1500;
		bolt->think = Pangea_BrandLand;
	} else {
		bolt->nextthink = level.time + 8000;
		bolt->think = G_FreeEntity;
	}
	bolt->s.pos.trType = TR_GRAVITY;
	bolt->s.pos.trTime = level.time - 50;		// MISSILE_PRESTEP_TIME of g_missile.c
	VectorCopy( muzzle, bolt->s.pos.trBase );
	VectorScale( fwd, a->speed, bolt->s.pos.trDelta );
	SnapVector( bolt->s.pos.trDelta );
	VectorCopy( muzzle, bolt->r.currentOrigin );
	// arrows and spears fly point first: cgame turns them along the velocity
	vectoangles( fwd, bolt->s.apos.trBase );
	bolt->s.apos.trType = TR_STATIONARY;

	if ( a->kind == PK_SPEAR ) {
		ent->client->pangeaSpearBack = level.time + PANGEA_SPEAR_BACK;
	}
	if ( a->kind == PK_BRAND ) {
		ent->client->pangeaTorchBack = level.time + PANGEA_TORCH_BACK;
		ent->client->ps.generic1 |= PSTAT_TORCH_OUT;
	}
}

/*
A spear lying on the ground: walk over it to take it (if your hand is empty).
*/
static void Pangea_SpearTouch( gentity_t *self, gentity_t *other, trace_t *trace ) {
	gclient_t *c = other->client;

	if ( !c || other->health <= 0 || !( c->ps.stats[STAT_WEAPONS] & ( 1 << WP_SHOTGUN ) ) ||
		c->ps.ammo[WP_SHOTGUN] > 0 ) {
		return;
	}
	c->ps.ammo[WP_SHOTGUN] = 1;
	c->pangeaSpearBack = 0;
	G_Sound( other, CHAN_AUTO, G_SoundIndex( "sound/misc/w_pkup.wav" ) );
	G_FreeEntity( self );
}

static void Pangea_DropSpear( const vec3_t at, const vec3_t dir ) {
	gentity_t	*sp = G_Spawn();
	trace_t		tr;
	vec3_t		down, origin, d;

	// the spear is stuck in the ground or lies at the victim's feet
	VectorCopy( at, origin );
	VectorCopy( at, down );
	down[2] -= 256;
	trap_Trace( &tr, origin, NULL, NULL, down, ENTITYNUM_NONE, MASK_SOLID );
	if ( tr.fraction < 1 && tr.fraction > 0 ) {
		VectorCopy( tr.endpos, origin );
		origin[2] += 4;
	}
	VectorCopy( dir, d );
	if ( VectorNormalize( d ) == 0 ) {
		VectorSet( d, 1, 0, 0 );
	}
	sp->classname = "pangea_spear";
	sp->s.eType = ET_GENERAL;
	sp->s.generic1 = PK_SPEAR_GROUND;
	sp->s.modelindex = G_ModelIndex( (char *)Pangea_KindModel( PK_SPEAR_GROUND ) );
	vectoangles( d, sp->s.apos.trBase );
	sp->s.apos.trType = TR_STATIONARY;
	// the point goes into the ground, the shaft sticks out behind it
	VectorMA( origin, -50, d, origin );
	if ( origin[2] < at[2] - 8 ) {
		origin[2] = at[2] - 8;
	}
	G_SetOrigin( sp, origin );
	VectorSet( sp->r.mins, -24, -24, -16 );
	VectorSet( sp->r.maxs, 24, 24, 32 );
	sp->r.contents = CONTENTS_TRIGGER;
	sp->touch = Pangea_SpearTouch;
	sp->nextthink = level.time + PANGEA_SPEAR_BACK;
	sp->think = G_FreeEntity;
	trap_LinkEntity( sp );
}

static void Pangea_FireThink( gentity_t *fire ) {
	int			touch[MAX_GENTITIES];
	vec3_t		mins, maxs;
	int			i, n;
	gentity_t	*owner = fire->r.ownerNum < ENTITYNUM_MAX_NORMAL ? &g_entities[fire->r.ownerNum] : NULL;

	if ( level.time >= fire->wait ) {
		G_FreeEntity( fire );
		return;
	}
	if ( owner && !owner->inuse ) {
		owner = NULL;
	}
	for ( i = 0 ; i < 3 ; i++ ) {
		mins[i] = fire->r.currentOrigin[i] - PANGEA_FIRE_RADIUS;
		maxs[i] = fire->r.currentOrigin[i] + PANGEA_FIRE_RADIUS;
	}
	n = trap_EntitiesInBox( mins, maxs, touch, MAX_GENTITIES );
	for ( i = 0 ; i < n ; i++ ) {
		gentity_t	*t = &g_entities[touch[i]];
		vec3_t		d;

		if ( !t->client || t->health <= 0 ) {
			continue;
		}
		VectorSubtract( t->r.currentOrigin, fire->r.currentOrigin, d );
		d[2] *= 0.5f;
		if ( VectorLength( d ) > PANGEA_FIRE_RADIUS ) {
			continue;
		}
		Pangea_Ignite( t, owner, 1500 );
	}
	fire->nextthink = level.time + PANGEA_BURN_TICK;
}

static void Pangea_SpawnFire( const vec3_t at, gentity_t *owner ) {
	gentity_t	*fire = G_Spawn();
	trace_t		tr;
	vec3_t		down, origin;

	VectorCopy( at, origin );
	VectorCopy( at, down );
	down[2] -= 128;
	trap_Trace( &tr, origin, NULL, NULL, down, ENTITYNUM_NONE, MASK_SOLID );
	if ( tr.fraction < 1 ) {
		VectorCopy( tr.endpos, origin );
	}
	origin[2] += 2;
	fire->classname = "pangea_fire";
	fire->s.eType = ET_GENERAL;
	fire->s.generic1 = PK_FIRE;
	fire->s.time = level.time;
	fire->r.ownerNum = owner ? owner->s.number : ENTITYNUM_NONE;
	fire->r.svFlags = SVF_BROADCAST;		// the light is seen from afar
	G_SetOrigin( fire, origin );
	fire->wait = level.time + PANGEA_FIRE_TIME;
	fire->think = Pangea_FireThink;
	fire->nextthink = level.time + 50;
	trap_LinkEntity( fire );
}

static void Pangea_BrandLand( gentity_t *brand ) {
	vec3_t origin;

	BG_EvaluateTrajectory( &brand->s.pos, level.time, origin );
	Pangea_SpawnFire( origin, brand->parent );
	G_FreeEntity( brand );
}

/*
Called first thing in G_MissileImpact for missiles with es->generic1 != PK_NONE.
qtrue = handled (the missile is gone or bounced).
*/
qboolean Pangea_MissileImpact( gentity_t *ent, trace_t *trace ) {
	const pangeaAbility_t	*a = Pangea_MissileAbility( ent );
	gentity_t				*other = &g_entities[trace->entityNum];
	gentity_t				*owner = &g_entities[ent->r.ownerNum];
	vec3_t					velocity, origin;
	int						kind = ent->s.generic1;

	if ( !a ) {
		return qfalse;
	}
	// the brand bounces off walls (stock bounce), lands by its think
	if ( !other->takedamage && ( ent->s.eFlags & ( EF_BOUNCE | EF_BOUNCE_HALF ) ) ) {
		return qfalse;
	}

	BG_EvaluateTrajectoryDelta( &ent->s.pos, level.time, velocity );
	VectorCopy( trace->endpos, origin );
	if ( other->takedamage ) {
		if ( VectorLength( velocity ) == 0 ) {
			velocity[2] = 1;
		}
		if ( LogAccuracyHit( other, owner ) ) {
			owner->client->accuracy_hits++;
		}
		G_Damage( other, ent, owner, velocity, origin, ent->damage, 0, ent->methodOfDeath );
		Pangea_Afflict( other, owner, a );
	}

	if ( other->takedamage && other->client ) {
		G_AddEvent( ent, EV_MISSILE_HIT, DirToByte( trace->plane.normal ) );
		ent->s.otherEntityNum = other->s.number;
	} else {
		G_AddEvent( ent, EV_MISSILE_MISS, DirToByte( trace->plane.normal ) );
	}

	if ( kind == PK_SPEAR ) {
		Pangea_DropSpear( other->client ? other->r.currentOrigin : origin, velocity );
	} else if ( kind == PK_BRAND ) {
		Pangea_SpawnFire( origin, owner );
	}

	// the missile turns into its own impact event, as G_MissileImpact does
	ent->freeAfterEvent = qtrue;
	ent->s.eType = ET_GENERAL;
	SnapVectorTowards( trace->endpos, ent->s.pos.trBase );
	G_SetOrigin( ent, trace->endpos );
	trap_LinkEntity( ent );
	return qtrue;
}

/*
Shield slam: the leap is done by Pmove, the shock ring here.
*/
static void Pangea_Slam( gentity_t *ent, const pangeaAbility_t *a ) {
	int		touch[MAX_GENTITIES];
	vec3_t	mins, maxs;
	int		i, n;

	for ( i = 0 ; i < 3 ; i++ ) {
		mins[i] = ent->r.currentOrigin[i] - PANGEA_SLAM_RADIUS;
		maxs[i] = ent->r.currentOrigin[i] + PANGEA_SLAM_RADIUS;
	}
	n = trap_EntitiesInBox( mins, maxs, touch, MAX_GENTITIES );
	for ( i = 0 ; i < n ; i++ ) {
		gentity_t	*t = &g_entities[touch[i]];
		vec3_t		d;

		if ( t == ent || !t->client || t->health <= 0 ) {
			continue;
		}
		VectorSubtract( t->r.currentOrigin, ent->r.currentOrigin, d );
		if ( VectorLength( d ) > PANGEA_SLAM_RADIUS ) {
			continue;
		}
		G_Damage( t, ent, ent, d, t->r.currentOrigin, a->damage * Pangea_DamageScale( ent ), DAMAGE_NO_KNOCKBACK, a->mod );
		Pangea_Push( t, d, PANGEA_SLAM_PUSH, 200 );
	}
}

static void Pangea_Use( gentity_t *ent, const pangeaAbility_t *a ) {
	if ( !a ) {
		return;
	}
	if ( trap_Cvar_VariableIntegerValue( "g_pangea_debug" ) ) {
		G_LogPrintf( "Pangea: use %i %s\n", ent->s.number, a->id );
	}
	if ( a->weapon != WP_GAUNTLET ) {
		ent->client->accuracy_shots++;
	}
	switch ( a->prim ) {
	case PP_MELEE:
		Pangea_Melee( ent, a );
		break;
	case PP_MISSILE:
		Pangea_FireMissile( ent, a );
		break;
	case PP_SLAM:
		Pangea_Slam( ent, a );
		break;
	default:
		break;
	}
}

/* EV_FIRE_WEAPON in a tier-0 arena */
void Pangea_FirePrimary( gentity_t *ent ) {
	Pangea_Use( ent, BG_PangeaAbility( ent->s.weapon, qfalse, Pangea_Mode() ) );
}

/* EV_PANGEA_ALT, weapon = eventParm */
void Pangea_FireAlt( gentity_t *ent, int weapon ) {
	if ( Pangea_Mode() == PANGEA_SIM ) {
		return;
	}
	Pangea_Use( ent, BG_PangeaAbility( weapon, qtrue, Pangea_Mode() ) );
}

/*
Every ClientThink before Pmove: burning, bola, stun, shield speed, a new torch/spear.
ps->speed is already set for this frame.
*/
void Pangea_ClientThink( gentity_t *ent ) {
	gclient_t	*c = ent->client;
	int			flags;

	if ( Pangea_Mode() == PANGEA_SIM ) {
		return;
	}
	flags = c->ps.generic1 & ( PSTAT_BLOCKING | PSTAT_TORCH_OUT );

	if ( ent->health <= 0 ) {
		c->pangeaBurnUntil = c->pangeaEntangleUntil = c->pangeaStunUntil = 0;
	}
	if ( ent->waterlevel >= 2 ) {
		c->pangeaBurnUntil = 0;		// water puts the fire out
	}
	if ( c->pangeaBurnUntil > level.time ) {
		flags |= PSTAT_BURNING;
		if ( level.time >= c->pangeaBurnNext ) {
			gentity_t *by = c->pangeaBurnBy >= 0 ? &g_entities[c->pangeaBurnBy] : NULL;

			if ( by && ( !by->inuse || !by->client ) ) {
				by = NULL;
			}
			c->pangeaBurnNext = level.time + PANGEA_BURN_TICK;
			G_Damage( ent, NULL, by, NULL, NULL, PANGEA_BURN_DAMAGE, DAMAGE_NO_KNOCKBACK | DAMAGE_NO_ARMOR, MOD_PANGEA_BURN );
		}
	}
	if ( c->pangeaEntangleUntil > level.time ) {
		flags |= PSTAT_ENTANGLED;
		c->ps.speed *= PANGEA_ENTANGLE_SPEED;
	}
	if ( c->pangeaStunUntil > level.time ) {
		flags |= PSTAT_STUNNED;
	}
	if ( flags & PSTAT_BLOCKING ) {
		c->ps.speed *= PANGEA_BLOCK_SPEED;
	}
	if ( c->pangeaTorchBack && level.time >= c->pangeaTorchBack ) {
		c->pangeaTorchBack = 0;
		c->ps.ammo[WP_LIGHTNING] = 1;
		flags &= ~PSTAT_TORCH_OUT;
	}
	if ( c->pangeaSpearBack && level.time >= c->pangeaSpearBack ) {
		c->pangeaSpearBack = 0;
		if ( c->ps.ammo[WP_SHOTGUN] <= 0 ) {
			c->ps.ammo[WP_SHOTGUN] = 1;
		}
	}
	c->ps.generic1 = flags;
}

/*
Bots: the projectile speed botlib aims with (it knows the stock weapons only).
*/
void Pangea_BotWeaponInfo( int weapon, float *speed ) {
	const pangeaAbility_t *a = BG_PangeaAbility( weapon, qfalse, Pangea_Mode() );

	if ( a && a->prim == PP_MISSILE ) {
		*speed = a->speed;
	} else if ( a ) {
		*speed = 0;
	}
}

/*
Bots: which slot to fight with at this distance; 0 = let botlib choose.
Close: spear, club, fists. Far: bow, sling; without ammo they close in.
*/
int Pangea_BotChooseWeapon( gentity_t *ent, float enemyDist ) {
	playerState_t	*ps = &ent->client->ps;
	int				mode = Pangea_Mode();

#define HAS( w )	( ( ps->stats[STAT_WEAPONS] & ( 1 << ( w ) ) ) && BG_PangeaSlotAllowed( ( w ), mode ) )
	if ( mode == PANGEA_SIM ) {
		return 0;
	}
	if ( enemyDist > 160 ) {
		if ( HAS( WP_ROCKET_LAUNCHER ) && ps->ammo[WP_ROCKET_LAUNCHER] > 0 ) {
			return WP_ROCKET_LAUNCHER;
		}
		if ( HAS( WP_GRENADE_LAUNCHER ) && ps->ammo[WP_GRENADE_LAUNCHER] > 0 ) {
			return WP_GRENADE_LAUNCHER;
		}
	}
	if ( HAS( WP_SHOTGUN ) && ps->ammo[WP_SHOTGUN] > 0 ) {
		return WP_SHOTGUN;
	}
	if ( HAS( WP_MACHINEGUN ) ) {
		return WP_MACHINEGUN;
	}
	return WP_GAUNTLET;
#undef HAS
}
