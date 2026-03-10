# Debugging Silent Scraping Failures

## Overview
The application now logs all extraction attempts with full details. This helps debug accounts that fail silently.

## Where Logs Are Stored
- **Windows**: `%USERPROFILE%\AppData\Local\TwitterXDownloader\logs\`
- **Mac/Linux**: `~/AppData/Local/TwitterXDownloader/logs/`

Logs are named: `extractor_YYYY-MM-DD_HH-MM-SS.log`

## Finding Failed Accounts

Look for these patterns in the log file:

### 1. Error Pattern
```
[ERROR] YYYY-MM-DD HH:MM:SS - Extraction failed for @username (timeline_type): error message
```

### 2. Warning Pattern  
```
[WARN] YYYY-MM-DD HH:MM:SS - Unable to parse JSON from extractor output for @username. Output length: XXX bytes
```

### 3. Debug Info Pattern
```
[DEBUG] YYYY-MM-DD HH:MM:SS - Extracted XXX media items and XXX metadata entries for @username
```

## Interpreting the Logs

### Full Extraction Log Entry
Each extraction attempt is logged as:
```
=== EXTRACTOR CALL ===
Timestamp: YYYY-MM-DD HH:MM:SS
Username: @username
Timeline Type: media/timeline/tweets/likes/bookmarks/etc
Duration: Xms
Exit Code: 0 (success) or non-zero (failure)

Command Args:
  [0]: URL
  [1]: --auth-token
  [2]: token_value
  ... (all arguments)

--- STDOUT (first 2000 chars) ---
[full output from extractor]

--- STDERR (first 2000 chars) ---
[error output if any]
```

## Common Issues and Troubleshooting

### Issue 1: Exit Code 0 but Empty Response
**Symptom**: Log shows exit code 0 but "Unable to parse JSON" warning
**Cause**: Extractor succeeded but returned no data (timeline empty or account inaccessible)
**Solution**: 
- Check if account exists and is public
- Verify auth token is valid
- Try with a known working account to compare

### Issue 2: Exit Code Non-Zero (Failed)
**Symptom**: Log shows exit code >0 or error in STDERR
**Causes could be**:
- Rate limited (HTTP 429)
- Authentication failed (401)  
- Account not found (404)
- Account protected (403)
- Network error

**Solution**:
- Look at the error message in STDERR
- Wait if rate limited
- Verify auth token if unauthorized

### Issue 3: Timeout or Very Slow Extraction
**Symptom**: Duration shows very large time value (>30000ms)
**Causes**:
- Network issues
- Rate limiting causing retries
- Large timeline
**Solution**:
- Check internet connection
- Reduce batch size
- Try later if rate limited

### Issue 4: Zero Media/Metadata Extracted
**Symptom**: Log shows "Extracted 0 media items and 0 metadata entries"
**Causes**:
- Account has no media
- Only text tweets (need to use "text" media type)
- Account restricted
**Solution**:
- Verify account has media
- Check media filter settings
- Try different timeline types

## How to Access Logs from the App

If a future frontend feature is added:
```javascript
// Call this from frontend
const logs = await ipc.GetDebugLogs(100);  // Get last 100 lines
const size = await ipc.GetDebugLogSize();  // Get log file size
```

## What to Share When Reporting Issues

If a specific account consistently fails, share:
1. The account username (with `@`)
2. The timeline type being scraped (media, likes, bookmarks, etc)
3. The relevant section from the log file showing:
   - The command arguments (with auth token redacted)
   - Full STDOUT and STDERR output
   - The exit code and duration

This helps identify the root cause quickly.
