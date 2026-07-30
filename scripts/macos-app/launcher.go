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
	response, err := client.Get("http://localhost:8501/_stcore/health")
	if err != nil {
		return false
	}
	defer response.Body.Close()
	return response.StatusCode >= 200 && response.StatusCode < 300
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
	missedChecks := 0
	for missedChecks < 10 {
		time.Sleep(3 * time.Second)
		if serverIsHealthy(client) {
			missedChecks = 0
		} else {
			missedChecks++
		}
	}
}
