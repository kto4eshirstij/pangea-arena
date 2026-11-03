# Фикстуры логов ioq3ded

Настоящий stdout `ioq3ded` (наша сборка, паки OpenArena), записан 2026-11-02 на ноутбуке:

- `duel-bots.log` — `oa_dm7`, `g_gametype 1`, rail + instagib, fraglimit 3, два бота (sarge, grism).
- `duel-npc.log` — записан 2026-11-03 здесь: `oa_dm7`, `g_gametype 1`, rail + instagib, fraglimit 3; NPC-бот
  `addbot sarge 3 free 0 Ker` против `grism`. `Ker` выиграл 3:0. Правка: `grism` (клиент 1) → билет `t2`.
- `ffa-bots.log` — `oa_dm4`, `g_gametype 0`, rocket, fraglimit 4 / timelimit 4, три бота; кончился по времени.

Единственная правка: боты пишут `Pangea: ticket bot client N`, здесь заменено на `t1`, `t2`, `t3`
(клиент N → билет t(N+1)), чтобы проверить сопоставление клиент → билет. Логи матчей людей по
LAN записать при проверке с Windows и положить сюда же (`duel-lan.log`, `ffa-lan.log`).
