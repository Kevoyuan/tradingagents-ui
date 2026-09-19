package main

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

func projectDirectory() (string, error) {
	executable, err := os.Executable()
	if err != nil {
		return "", err
	}

	projectDir := executable
	for range 4 {
		projectDir = filepath.Dir(projectDir)
	}
	return projectDir, nil
}

func showLaunchError() {
	_ = exec.Command(
		"/usr/bin/osascript",
		"-e",
		`display alert "TradingAgents UI could not start" message "Check ~/Library/Logs/tradingagents-ui/streamlit.log for details." as critical`,
	).Run()
}

func serverIsHealthy(client *http.Client) bool {
	response, err := client.Get(healthURL())
	if err != nil {
		return false
	}
	defer response.Body.Close()
	return response.StatusCode >= 200 && response.StatusCode < 300
}

func healthURL() string {
	port := os.Getenv("TRADINGAGENTS_UI_PORT")
	if port == "" {
		port = "8501"
	}
	return fmt.Sprintf("http://localhost:%s/_stcore/health", port)
}

func main() {
	projectDir, err := projectDirectory()
	if err != nil {
		showLaunchError()
		return
	}
	launchScript := filepath.Join(projectDir, "scripts", "launch-local-webapp.sh")
	launchCommand := filepath.Join(
		os.TempDir(),
		fmt.Sprintf("tradingagents-ui-launch-%d.command", os.Getuid()),
	)
	commandContents := fmt.Sprintf(
		"#!/bin/bash\nexec /bin/bash %q\n",
		launchScript,
	)
	if err := os.WriteFile(launchCommand, []byte(commandContents), 0700); err != nil {
		showLaunchError()
		return
	}

	if err := exec.Command(
		"/usr/bin/open",
		"-gj",
		"-a",
		"Terminal",
		launchCommand,
	).Run(); err != nil {
		showLaunchError()
		return
	}

	client := &http.Client{Timeout: 2 * time.Second}
	// Exit as soon as the server is up so LaunchServices does not treat the
	// app as running forever, which makes later double-clicks a no-op.
	deadline := time.Now().Add(45 * time.Second)
	for time.Now().Before(deadline) {
		if serverIsHealthy(client) {
			// Give the launch script a moment to bring the browser window up
			// before this process exits.
			time.Sleep(2 * time.Second)
			return
		}
		time.Sleep(2 * time.Second)
	}
}
