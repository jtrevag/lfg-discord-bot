# Game Tracking Feature Testing Guide

Complete end-to-end testing checklist for the game tracking feature.

## Prerequisites

1. Bot deployed with latest code
2. At least 4 Discord users available for testing (or use alt accounts)
3. `sqlite3` installed on server: `sudo apt-get install sqlite3`

---

## Part 1: Initial Setup Verification

### 1.1 Check Bot Started Successfully

```bash
# On your server
docker-compose ps

# Should show: commander-pod-bot (Up)
```

### 1.2 Verify Database Initialization

```bash
# Check logs
docker-compose logs commander-pod-bot | grep -i database

# Expected output:
# "Database initialized and verified"
# "Checking for incomplete polls..."
# "No incomplete polls found." (on first run)
```

### 1.3 Verify Database File Created

```bash
# Check file exists
ls -la data/

# Should show:
# lfg_bot.db (database file)
```

### 1.4 Inspect Database Structure

```bash
# Connect to database
sqlite3 data/lfg_bot.db

# Inside sqlite3 prompt:
.tables
# Expected: league, player, poll, pod, gameresult, playerstats

SELECT * FROM league;
# Expected: 1 row - "Season 2026" with is_active=1

SELECT COUNT(*) FROM poll;
# Expected: 0 (no polls yet)

.quit
```

**✅ Checkpoint:** Database created with default league

---

## Part 2: Poll Creation and Completion

### 2.1 Create a Test Poll

**In Discord:**
```
!createpoll
```

**Expected:**
- Poll posted with 3 day options (Monday, Tuesday, Wednesday)
- Poll duration: 24 hours
- Message: "Weekly Commander Game Poll"

### 2.2 Vote on the Poll

**Have at least 4 users vote** (need minimum for 1 pod):
- User 1: Vote Monday, Tuesday
- User 2: Vote Monday
- User 3: Vote Monday
- User 4: Vote Monday, Wednesday

### 2.3 Wait for Poll to Complete

**Option A: Wait 24 hours** (natural flow)

**Option B: For quick testing**, manually trigger:
```
!calculatepods
```

### 2.4 Verify Poll Saved to Database

```bash
# Check poll was saved
sqlite3 data/lfg_bot.db "SELECT id, discord_message_id, created_at FROM poll;"

# Expected: 1 row with poll data
```

### 2.5 Verify Pods Saved to Database

```bash
# Check pods created
sqlite3 data/lfg_bot.db "SELECT id, day_of_week, status, player1_id, player2_id, player3_id, player4_id FROM pod;"

# Expected: 1+ rows with status='scheduled'
```

### 2.6 Verify Bot Logs

```bash
docker-compose logs commander-pod-bot | grep "Saved.*pods to database"

# Expected: "Saved 1 pods to database (poll ID: 1)"
```

**✅ Checkpoint:** Poll and pods saved to database

---

## Part 3: Interactive Button Testing

### 3.1 Verify Buttons Appeared

**In Discord, check the bot's pod messages:**
- Each pod should have a green "Game Completed ✅" button
- Format: "Pod 1: @User1, @User2, @User3, @User4"

### 3.2 Click "Game Completed" Button

**Action:** Click the green button

**Expected:**
- Modal form appears with title "Report Game Result"
- Dropdown showing 4 players (should show real names if mapped, or "Player [ID]")
- Optional "Game Notes" text field

### 3.3 Test Without Player Mapping (First Time)

**In the modal:**
1. Select a winner from dropdown (will show as "Player 123456789")
2. Add optional note: "Test game"
3. Click Submit

**Expected:**
- Confirmation dialog appears (only visible to you)
- Message: "⚠️ Confirm winner: <@123456789> Is this correct?"
- Two buttons: "✅ Yes, Confirm" and "❌ Cancel"

### 3.4 Test Confirmation Cancel

**Action:** Click "❌ Cancel"

**Expected:**
- Message updates: "❌ Cancelled. Click the 'Game Completed' button to try again."
- Button still on original pod message
- No database record created

### 3.5 Submit Actual Result

**Action:**
1. Click "Game Completed ✅" button again
2. Select winner
3. Click Submit
4. Click "✅ Yes, Confirm"

**Expected:**
- Confirmation message: "✅ Game result recorded! Winner: <@user>"
- Original pod message updates with:
  ```
  Pod 1: @User1, @User2, @User3, @User4

  ✅ Completed - Winner: <@User1>
  Reported by <@User2> on Jan 11, 3:45 PM
  Notes: Test game
  ```
- Button removed from pod message

### 3.6 Verify Result in Database

```bash
sqlite3 data/lfg_bot.db "SELECT * FROM gameresult;"

# Expected: 1 row with winner_id, reported_by_id, notes
```

### 3.7 Test Duplicate Prevention

**Action:** Try to click the button on the same pod again

**Expected:**
- Error message: "❌ This game has already been reported!"
- No modal appears

**✅ Checkpoint:** Interactive buttons work correctly

---

## Part 4: Player Name Mapping

### 4.1 Map Players to Real Names

**In Discord (as admin):**
```
!mapplayer @User1 Patrick
!mapplayer @User2 John
!mapplayer @User3 Matt
!mapplayer @User4 Zaq
```

**Expected:** Each command responds with:
- "✅ Mapped @User → Patrick"

### 4.2 Test Updating a Mapping

```
!mapplayer @User1 Patrick Updated
```

**Expected:**
- "✅ Updated @User1: **Patrick** → **Patrick Updated**"

### 4.3 View All Mappings

```
!listmappings
```

**Expected:**
```
👥 Player Name Mappings

<@User1> → **Patrick Updated**
<@User2> → **John**
<@User3> → **Matt**
<@User4> → **Zaq**
```

### 4.4 Verify Database

```bash
sqlite3 data/lfg_bot.db "SELECT discord_user_id, real_name FROM player;"

# Expected: 4 rows with mappings
```

### 4.5 Test Button with Mapped Names

**Action:** Create a new poll, complete it, click "Game Completed"

**Expected:**
- Modal dropdown now shows: "Patrick", "John", "Matt", "Zaq" instead of "Player [ID]"
- Completion message shows: "Winner: @User1 (Patrick)"

**✅ Checkpoint:** Player name mapping working

---

## Part 5: Statistics Commands

### 5.1 Test Leaderboard

```
!leaderboard
```

**Expected:**
```
🏆 Season 2026 Leaderboard
(Minimum 3 games)

No statistics yet for Season 2026.
Play some games first!
```
*(Won't show data until 3 games played)*

### 5.2 Test Individual Stats

```
!stats @User1
```

**Expected:**
```
📊 Stats for <@User1> (Patrick)
League: Season 2026

Games Played: 1
Games Won: 1
Win Rate: 100.0%
```

### 5.3 Test Stats for Non-Player

```
!stats @UnmappedUser
```

**Expected:**
- "No stats found for @UnmappedUser in Season 2026. They haven't played any games yet!"

### 5.4 Create More Games for Testing

**Action:** Complete 2 more polls with different winners

**Then test leaderboard:**
```
!leaderboard
```

**Expected:**
```
🏆 Season 2026 Leaderboard
(Minimum 3 games)

1. <@User1> (Patrick) - 66.7% (2W / 3G)
2. <@User2> (John) - 33.3% (1W / 3G)
```

### 5.5 Test Head-to-Head

```
!headtohead @User1 @User2
```

**Expected:**
```
⚔️ <@User1> (Patrick) vs <@User2> (John)
League: Season 2026

Games Together: 3
<@User1> (Patrick) Wins: 2 (66.7%)
<@User2> (John) Wins: 1 (33.3%)
Other Wins: 0 (0.0%)
```

### 5.6 Test Recent Games

```
!recentgames 5
```

**Expected:**
```
🎮 Recent Games (Last 3)

Jan 11 - Monday: <@User1> (Patrick) won
  (vs <@User2> (John), <@User3> (Matt), <@User4> (Zaq))
Jan 11 - Monday: <@User2> (John) won
  (vs <@User1> (Patrick), <@User3> (Matt), <@User4> (Zaq))
...
```

**✅ Checkpoint:** Statistics commands working

---

## Part 6: League Management

### 6.1 View Current League

```
!currentleague
```

**Expected:**
```
📅 Current League: Season 2026

Started: Jan 11, 2026
Games Played: 3
```

### 6.2 List All Leagues

```
!leagues
```

**Expected:**
```
📚 All Leagues

🟢 Season 2026 (Jan 11, 2026 - Present) - 3 games
```

### 6.3 Create New League

```
!createleague 2026-02-01 Spring Season
```

**Expected:**
```
✅ Created new league: Spring Season
Start date: Feb 01, 2026
Previous league archived.
```

### 6.4 Verify Previous League Archived

```
!leagues
```

**Expected:**
```
📚 All Leagues

🟢 Spring Season (Feb 01, 2026 - Present) - 0 games
⚪ Season 2026 (Jan 11, 2026 - Feb 01, 2026) - 3 games
```

### 6.5 Check Database

```bash
sqlite3 data/lfg_bot.db "SELECT name, is_active, start_date, end_date FROM league ORDER BY start_date DESC;"

# Expected:
# Spring Season|1|2026-02-01|
# Season 2026|0|2026-01-11|2026-02-01
```

### 6.6 Test Stats in Old League

```
!stats @User1 Season 2026
```

**Expected:**
- Shows stats from archived league

**✅ Checkpoint:** League management working

---

## Part 7: Admin Commands

### 7.1 Test Manual Game Completion

**Action:** Create a pod without using the button

```
!completegame 1 @User1
```

**Expected:**
- "✅ Game 1 marked complete. Winner: <@User1> (Patrick)"

### 7.2 Test Edit Game Result

```
!editgame 1 @User2
```

**Expected:**
```
✅ Game 1 updated.
New winner: <@User2> (John)
Previous winner: <@User1> (Patrick)
```

### 7.3 Verify Stats Updated

```
!stats @User1
!stats @User2
```

**Expected:**
- User1's wins decreased by 1
- User2's wins increased by 1

### 7.4 Check Database

```bash
sqlite3 data/lfg_bot.db "SELECT pod_id, winner_id, notes FROM gameresult WHERE pod_id = 1;"

# Notes should show: "[Edited by admin on 2026-01-11]"
```

**✅ Checkpoint:** Admin commands working

---

## Part 8: Google Sheets Import (Optional)

### 8.1 Setup Google Credentials

**Prerequisites:**
1. Create Google Cloud service account
2. Download credentials JSON
3. Save as `config/google-credentials.json`
4. Share your Google Sheet with service account email

### 8.2 Prepare Google Sheet

**Create sheet with columns:**
- Week | Player 1 | Player 2 | Player 3 | Player 4 | Winner

**Example data:**
```
W0    Patrick    John    Matt    Zaq    Patrick
W1    Patrick    John    Matt    Zaq    John
W2    Patrick    John    Matt    Zaq    Matt
```

### 8.3 Map All Players First

```
!mapplayer @User1 Patrick
!mapplayer @User2 John
!mapplayer @User3 Matt
!mapplayer @User4 Zaq
```

### 8.4 Create Historical League

```
!createleague 2025-01-01 Historical Games
```

### 8.5 Import Sheet

```
!importsheet https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID Historical Games
```

**Expected:**
```
✅ Import Complete!

League: Historical Games
Games Imported: 3
Pods Created: 3
```

### 8.6 Verify Import

```
!leaderboard Historical Games
```

**Expected:**
- Shows leaderboard from imported data

### 8.7 Check Database

```bash
sqlite3 data/lfg_bot.db "
SELECT COUNT(*) FROM gameresult gr
JOIN pod p ON gr.pod_id = p.id
JOIN poll po ON p.poll_id = po.id
JOIN league l ON po.league_id = l.id
WHERE l.name = 'Historical Games';
"

# Expected: 3 (number of imported games)
```

**✅ Checkpoint:** Google Sheets import working

---

## Part 9: Error Handling and Edge Cases

### 9.1 Test Button on Completed Game

**Action:** Click "Game Completed" on already-completed pod

**Expected:**
- "❌ This game has already been reported!"

### 9.2 Test Commands with Missing Data

```
!stats @NonExistentUser
!leaderboard NonExistentLeague
!headtohead @User1 @User5
```

**Expected:**
- Appropriate error messages for each

### 9.3 Test Import Without Mappings

**Action:** Try import without mapping all players

**Expected:**
```
❌ Import failed: [error details]

Make sure:
1. All players are mapped (!mapplayer)
2. Sheet is publicly readable
3. Sheet has correct columns...
```

### 9.4 Test Permission Checks

**As non-admin user:**
```
!completegame 1 @User1
!editgame 1 @User1
!mapplayer @User1 Test
!createleague 2026-01-01 Test
!importsheet https://... Test
```

**Expected:**
- "You don't have permission to use this command."

### 9.5 Test Bot Restart Recovery

**Action:**
1. Create a poll
2. Stop bot: `docker-compose down`
3. Wait for poll to end (or end manually in Discord)
4. Start bot: `docker-compose up -d`

**Expected:**
```
# In logs:
Found 1 poll(s) that might need processing
Processing completed poll: [message_id]
✅ Successfully processed 1 incomplete poll(s)
```

**✅ Checkpoint:** Error handling working correctly

---

## Part 10: Performance and Data Integrity

### 10.1 Database Integrity Check

```bash
sqlite3 data/lfg_bot.db "PRAGMA integrity_check;"

# Expected: ok
```

### 10.2 Check Foreign Key Constraints

```bash
sqlite3 data/lfg_bot.db "PRAGMA foreign_key_check;"

# Expected: (empty result = no violations)
```

### 10.3 Verify All Pods Have Results or Are Scheduled

```bash
sqlite3 data/lfg_bot.db "
SELECT p.id, p.status, gr.id as result_id
FROM pod p
LEFT JOIN gameresult gr ON gr.pod_id = p.id;
"

# Check: completed pods should have result_id, scheduled pods should not
```

### 10.4 Check Stats Consistency

```bash
sqlite3 data/lfg_bot.db "
SELECT
    ps.player_id,
    ps.games_won,
    ps.games_played,
    ps.win_rate,
    (CAST(ps.games_won AS FLOAT) / ps.games_played * 100) as calculated_win_rate
FROM playerstats ps
WHERE ps.games_played > 0;
"

# Verify win_rate matches calculated_win_rate
```

### 10.5 Database Size Check

```bash
ls -lh data/lfg_bot.db

# Should be reasonable (few KB for test data)
```

**✅ Checkpoint:** Database integrity verified

---

## Summary Checklist

Use this quick checklist to verify all features:

- [ ] Database created and initialized
- [ ] Default league created (Season 2026)
- [ ] Poll created and saved to database
- [ ] Pods saved to database after poll completion
- [ ] Interactive buttons appear on pods
- [ ] Winner selection modal works
- [ ] Confirmation dialog prevents mistakes
- [ ] Game result saved to database
- [ ] Pod message updates after completion
- [ ] Player name mapping works (!mapplayer, !listmappings)
- [ ] Leaderboard shows correct stats (!leaderboard)
- [ ] Individual stats work (!stats)
- [ ] Head-to-head stats work (!headtohead)
- [ ] Recent games display (!recentgames)
- [ ] League management works (!createleague, !currentleague, !leagues)
- [ ] Admin commands work (!completegame, !editgame)
- [ ] Google Sheets import works (!importsheet) *(optional)*
- [ ] Error handling works (duplicate reports, missing data)
- [ ] Permission checks work (admin-only commands)
- [ ] Bot restart recovery works (incomplete polls)
- [ ] Database integrity verified

---

## Troubleshooting

### Issue: Button doesn't respond
**Solution:** Check logs for errors:
```bash
docker-compose logs -f | grep -i error
```

### Issue: Modal doesn't show player names
**Solution:** Map players using `!mapplayer` command

### Issue: Stats show 0.0% for everyone
**Solution:** Check that games have been completed and stats updated:
```bash
sqlite3 data/lfg_bot.db "SELECT * FROM gameresult;"
sqlite3 data/lfg_bot.db "SELECT * FROM playerstats;"
```

### Issue: Import fails
**Solution:**
1. Verify all players mapped: `!listmappings`
2. Check credentials file exists: `ls config/google-credentials.json`
3. Verify sheet is shared with service account email
4. Check sheet has exact column names: Week, Player 1, Player 2, Player 3, Player 4, Winner

### Issue: Database locked error
**Solution:** Close any open sqlite3 connections:
```bash
# Kill all sqlite3 processes
killall sqlite3
```

---

## Complete Test Results Template

Use this template to document your test results:

```
Date: ___________
Tester: ___________
Branch: feature/game-tracking
Commit: ___________

Part 1: Initial Setup ✅/❌
Part 2: Poll Creation ✅/❌
Part 3: Interactive Buttons ✅/❌
Part 4: Player Mapping ✅/❌
Part 5: Statistics ✅/❌
Part 6: League Management ✅/❌
Part 7: Admin Commands ✅/❌
Part 8: Google Sheets Import ✅/❌ (optional)
Part 9: Error Handling ✅/❌
Part 10: Data Integrity ✅/❌

Issues Found:
1.
2.
3.

Overall Status: PASS / FAIL / NEEDS REVIEW
```
