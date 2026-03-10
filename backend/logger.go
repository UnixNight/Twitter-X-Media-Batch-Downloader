package backend

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Logger handles logging of scraping operations
type Logger struct {
	mu       sync.Mutex
	logFile  *os.File
	logDir   string
	filePath string
}

var globalLogger *Logger

// InitLogger initializes the global logger
func InitLogger(logsDir string) error {
	if globalLogger != nil {
		globalLogger.Close()
	}

	// Create logs directory if it doesn't exist
	if err := os.MkdirAll(logsDir, 0755); err != nil {
		return fmt.Errorf("failed to create logs directory: %v", err)
	}

	// Create log file with timestamp
	timestamp := time.Now().Format("2006-01-02_15-04-05")
	logFile := filepath.Join(logsDir, fmt.Sprintf("extractor_%s.log", timestamp))

	file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return fmt.Errorf("failed to create log file: %v", err)
	}

	globalLogger = &Logger{
		logFile:  file,
		logDir:   logsDir,
		filePath: logFile,
	}

	return nil
}

// LogExtractorCall logs an extractor command call with all details
func LogExtractorCall(username, timelineType string, args []string, exitCode int, stdout string, stderr string, duration time.Duration) {
	if globalLogger == nil {
		return
	}

	globalLogger.mu.Lock()
	defer globalLogger.mu.Unlock()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Fprintf(globalLogger.logFile, "\n=== EXTRACTOR CALL ===\n")
	fmt.Fprintf(globalLogger.logFile, "Timestamp: %s\n", timestamp)
	fmt.Fprintf(globalLogger.logFile, "Username: %s\n", username)
	fmt.Fprintf(globalLogger.logFile, "Timeline Type: %s\n", timelineType)
	fmt.Fprintf(globalLogger.logFile, "Duration: %v\n", duration)
	fmt.Fprintf(globalLogger.logFile, "Exit Code: %d\n", exitCode)
	fmt.Fprintf(globalLogger.logFile, "\nCommand Args:\n")
	for i, arg := range args {
		fmt.Fprintf(globalLogger.logFile, "  [%d]: %s\n", i, arg)
	}
	fmt.Fprintf(globalLogger.logFile, "\n--- STDOUT (first 2000 chars) ---\n")
	if len(stdout) > 2000 {
		fmt.Fprintf(globalLogger.logFile, "%s\n... (truncated)\n", stdout[:2000])
	} else {
		fmt.Fprintf(globalLogger.logFile, "%s\n", stdout)
	}
	fmt.Fprintf(globalLogger.logFile, "\n--- STDERR (first 2000 chars) ---\n")
	if len(stderr) > 2000 {
		fmt.Fprintf(globalLogger.logFile, "%s\n... (truncated)\n", stderr[:2000])
	} else {
		fmt.Fprintf(globalLogger.logFile, "%s\n", stderr)
	}
	fmt.Fprintf(globalLogger.logFile, "\n")
	globalLogger.logFile.Sync()
}

// LogDebug logs a debug message
func LogDebug(format string, args ...interface{}) {
	if globalLogger == nil {
		return
	}

	globalLogger.mu.Lock()
	defer globalLogger.mu.Unlock()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Fprintf(globalLogger.logFile, "[DEBUG] %s - %s\n", timestamp, fmt.Sprintf(format, args...))
	globalLogger.logFile.Sync()
}

// LogError logs an error message
func LogError(format string, args ...interface{}) {
	if globalLogger == nil {
		return
	}

	globalLogger.mu.Lock()
	defer globalLogger.mu.Unlock()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Fprintf(globalLogger.logFile, "[ERROR] %s - %s\n", timestamp, fmt.Sprintf(format, args...))
	globalLogger.logFile.Sync()
}

// LogWarning logs a warning message
func LogWarning(format string, args ...interface{}) {
	if globalLogger == nil {
		return
	}

	globalLogger.mu.Lock()
	defer globalLogger.mu.Unlock()

	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Fprintf(globalLogger.logFile, "[WARN] %s - %s\n", timestamp, fmt.Sprintf(format, args...))
	globalLogger.logFile.Sync()
}

// GetLatestLogs reads the latest log file and returns its contents
func GetLatestLogs(maxLines int) (string, error) {
	if globalLogger == nil {
		return "", fmt.Errorf("logger not initialized")
	}

	globalLogger.mu.Lock()
	defer globalLogger.mu.Unlock()

	// Re-open the file for reading to get latest content
	file, err := os.Open(globalLogger.filePath)
	if err != nil {
		return "", fmt.Errorf("failed to open log file: %v", err)
	}
	defer file.Close()

	// Read file content
	stat, err := file.Stat()
	if err != nil {
		return "", fmt.Errorf("failed to stat file: %v", err)
	}

	// For large files, only read the last 100KB
	maxReadSize := int64(100 * 1024)
	startPos := stat.Size() - maxReadSize
	if startPos < 0 {
		startPos = 0
	}

	buf := make([]byte, stat.Size()-startPos)
	_, err = file.ReadAt(buf, startPos)
	if err != nil && err.Error() != "EOF" {
		return "", fmt.Errorf("failed to read log file: %v", err)
	}

	return string(buf), nil
}

// GetLogFileSize returns the size of the current log file in bytes
func GetLogFileSize() int64 {
	if globalLogger == nil {
		return 0
	}

	globalLogger.mu.Lock()
	defer globalLogger.mu.Unlock()

	stat, err := os.Stat(globalLogger.filePath)
	if err != nil {
		return 0
	}
	return stat.Size()
}

// Close closes the logger
func (l *Logger) Close() {
	if l != nil && l.logFile != nil {
		l.logFile.Close()
	}
}

// CloseLogger closes the global logger
func CloseLogger() {
	if globalLogger != nil {
		globalLogger.Close()
	}
}
