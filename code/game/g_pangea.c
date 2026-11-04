/*
===========================================================================
Pangea Arena match rules. Copyright (C) 2026 Pangea contributors.

This file is part of Pangea Arena, a fork of ioquake3, and is distributed
under the terms of the GNU General Public License version 2 or later
(see COPYING.txt).
===========================================================================

Rules are plain cvars set by the match manager on the ioq3ded command line:

  g_pangea_tickets   "t1,t2,..."  only clients with userinfo pangea_ticket in the list
  g_pangea_arsenal   full | rail | rocket | melee
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
	return PANGEA_ARSENAL_FULL;
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
Called from ClientConnect after the client slot was reset and accepted.
*/
void Pangea_ClientConnected( int clientNum, const char *userinfo, qboolean isBot ) {
	if ( !Pangea_Active() ) {
		return;
	}
	Q_strncpyz( pangeaTickets[clientNum], isBot ? "bot" : Info_ValueForKey( userinfo, "pangea_ticket" ),
		sizeof( pangeaTickets[clientNum] ) );
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

int Pangea_ModifyDamage( int damage, int mod ) {
	if ( g_pangea_instagib.integer && mod == MOD_RAILGUN ) {
		return 1000;
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
