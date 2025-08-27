#!/usr/bin/env python3
"""
TradingAgents Web Dashboard - Separate UI Application
Interactive web interface for the TradingAgents multi-agent system
"""

import os
import requests
import json
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import threading
import time

app = Flask(__name__)

# Configuration
TRADINGAGENTS_API_URL = os.getenv("TRADINGAGENTS_API_URL", "https://stock-prediction-model-x5mr.onrender.com")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 8002))

# Global storage for analysis results
analysis_results = {}
analysis_status = {}

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingAgents Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        
        .header h1 {
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #7f8c8d;
            font-size: 1.2em;
        }
        
        .analysis-form {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .form-group {
            display: flex;
            gap: 15px;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .form-group input {
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.3s;
            min-width: 200px;
        }
        
        .form-group input:focus {
            border-color: #667eea;
        }
        
        .btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .status-section {
            margin-bottom: 30px;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .status-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
        }
        
        .status-card h3 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background-color: #27ae60; }
        .status-warning { background-color: #f39c12; }
        .status-error { background-color: #e74c3c; }
        
        .progress-section {
            margin-bottom: 30px;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #667eea, #764ba2);
            border-radius: 4px;
            transition: width 0.5s ease;
            width: 0%;
        }
        
        .agent-status {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .agent-card {
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        
        .agent-card.active {
            border: 2px solid #667eea;
            background: linear-gradient(135deg, #667eea11, #764ba211);
        }
        
        .results-section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .results-section h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        
        .decision-card {
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            color: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 1.3em;
            font-weight: bold;
        }
        
        .decision-card.sell {
            background: linear-gradient(135deg, #e74c3c, #c0392b);
        }
        
        .decision-card.hold {
            background: linear-gradient(135deg, #f39c12, #e67e22);
        }
        
        .analysis-details {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.4;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .loading {
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
        }
        
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #f44336;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        .quick-symbols {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
            margin-top: 15px;
        }
        
        .symbol-btn {
            background: white;
            border: 2px solid #667eea;
            color: #667eea;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .symbol-btn:hover {
            background: #667eea;
            color: white;
        }

        /* Input container and autocomplete styles */
        .input-container {
            position: relative;
            display: flex;
            flex-direction: column;
        }

        .company-info {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
            min-height: 16px;
        }

        .autocomplete-dropdown {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 8px 8px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        }

        .autocomplete-item {
            padding: 12px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
        }

        .autocomplete-item:hover {
            background: #f8f9fa;
        }

        .autocomplete-item:last-child {
            border-bottom: none;
        }

        .autocomplete-symbol {
            font-weight: bold;
            color: #667eea;
        }

        .autocomplete-company {
            font-size: 12px;
            color: #666;
            margin-top: 2px;
        }

        /* History section styles */
        .history-section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-top: 30px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }

        .history-section h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }

        .history-controls {
            margin-bottom: 20px;
        }

        .history-container {
            max-height: 400px;
            overflow-y: auto;
        }

        .history-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: all 0.3s;
        }

        .history-item:hover {
            background: #e9ecef;
            transform: translateY(-2px);
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
        }

        .history-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .history-symbol {
            font-weight: bold;
            font-size: 1.1em;
            color: #2c3e50;
        }

        .history-decision {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }

        .history-decision.buy {
            background: #d4edda;
            color: #155724;
        }

        .history-decision.sell {
            background: #f8d7da;
            color: #721c24;
        }

        .history-decision.hold {
            background: #fff3cd;
            color: #856404;
        }

        .history-meta {
            font-size: 12px;
            color: #666;
            display: flex;
            gap: 15px;
        }

        .history-date {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .history-duration {
            color: #2ecc71;
            font-weight: 500;
            font-size: 0.9em;
        }

        .history-actions {
            margin-top: 10px;
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }

        .download-btn {
            background: linear-gradient(45deg, #3498db, #2980b9);
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.85em;
            cursor: pointer;
            transition: all 0.3s;
            min-width: 60px;
        }

        .download-btn:hover {
            background: linear-gradient(45deg, #2980b9, #3498db);
            transform: translateY(-1px);
            box-shadow: 0 3px 8px rgba(52, 152, 219, 0.3);
        }

        .pdf-btn {
            background: linear-gradient(45deg, #e74c3c, #c0392b);
        }

        .pdf-btn:hover {
            background: linear-gradient(45deg, #c0392b, #e74c3c);
            box-shadow: 0 3px 8px rgba(231, 76, 60, 0.3);
        }

        /* Mobile Responsiveness */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .container {
                padding: 15px;
                border-radius: 15px;
            }
            
            .header h1 {
                font-size: 1.8em;
                margin-bottom: 5px;
            }
            
            .header p {
                font-size: 1em;
            }
            
            .analysis-form {
                padding: 20px;
                margin-bottom: 20px;
            }
            
            .form-group {
                flex-direction: column;
                gap: 10px;
                align-items: stretch;
            }
            
            .form-group input {
                min-width: auto;
                width: 100%;
            }
            
            .btn {
                width: 100%;
                padding: 15px;
                font-size: 18px;
            }
            
            .status-grid {
                grid-template-columns: 1fr;
                gap: 15px;
            }
            
            .status-card {
                padding: 15px;
            }
            
            .status-card h3 {
                font-size: 1em;
            }
            
            .popular-stocks {
                justify-content: center;
            }
            
            .stock-btn {
                padding: 8px 12px;
                font-size: 14px;
                min-width: 60px;
            }
            
            .results-section {
                padding: 15px;
            }
            
            .results-section h2 {
                font-size: 1.3em;
            }
            
            .history-section {
                padding: 15px;
            }
            
            .history-section h2 {
                font-size: 1.3em;
            }
            
            .history-item {
                padding: 12px;
            }
            
            .history-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 5px;
            }
            
            .history-symbol {
                font-size: 1.1em;
            }
            
            .history-decision {
                font-size: 0.8em;
                padding: 3px 8px;
            }
            
            .autocomplete-dropdown {
                max-height: 200px;
            }
            
            .autocomplete-item {
                padding: 12px;
                font-size: 16px;
            }

            /* Mobile-specific improvements */
            .header {
                margin-bottom: 25px;
                padding-bottom: 15px;
            }
            
            .popular-stocks {
                flex-wrap: wrap;
                gap: 8px;
            }
            
            /* Improve touch targets */
            input, button, .stock-btn, .history-item {
                min-height: 44px; /* iOS/Android recommended minimum */
            }
            
            /* Prevent zoom on input focus */
            input {
                font-size: 16px;
            }
        }

        @media (max-width: 480px) {
            .header h1 {
                font-size: 1.5em;
            }
            
            .analysis-form {
                padding: 15px;
            }
            
            .stock-btn {
                padding: 6px 10px;
                font-size: 12px;
                min-width: 50px;
            }
            
            .status-card {
                padding: 12px;
            }
            
            .history-item {
                padding: 10px;
            }

            .history-actions {
                justify-content: center;
                margin-top: 8px;
            }

            .download-btn {
                font-size: 12px;
                padding: 6px 10px;
                min-width: 50px;
            }

            .history-actions {
                gap: 6px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 TradingAgents Dashboard</h1>
            <p>Multi-Agent LLM Financial Trading Analysis</p>
        </div>

        <div class="analysis-form">
            <form onsubmit="startAnalysis(event)">
                <div class="form-group">
                    <div class="input-container">
                        <input type="text" id="symbol" placeholder="Stock Symbol (e.g. AAPL, TSLA, NVDA)" required autocomplete="off">
                        <div id="companyInfo" class="company-info"></div>
                        <div id="autocomplete" class="autocomplete-dropdown"></div>
                    </div>
                    <input type="date" id="date" value="2025-08-27">
                    <button type="submit" id="analyzeBtn" class="btn">🔍 Start Analysis</button>
                </div>
                <div class="quick-symbols">
                    <span class="symbol-btn" onclick="setSymbol('AAPL')">AAPL</span>
                    <span class="symbol-btn" onclick="setSymbol('TSLA')">TSLA</span>
                    <span class="symbol-btn" onclick="setSymbol('NVDA')">NVDA</span>
                    <span class="symbol-btn" onclick="setSymbol('MSFT')">MSFT</span>
                    <span class="symbol-btn" onclick="setSymbol('GOOGL')">GOOGL</span>
                    <span class="symbol-btn" onclick="setSymbol('AMZN')">AMZN</span>
                </div>
            </form>
        </div>

        <div class="status-section">
            <div class="status-grid">
                <div class="status-card">
                    <h3>System Status</h3>
                    <p id="systemStatus"><span class="status-indicator status-warning"></span>Checking...</p>
                </div>
                <div class="status-card">
                    <h3>Analysis Progress</h3>
                    <p id="analysisProgress">Ready to analyze</p>
                </div>
                <div class="status-card">
                    <h3>Active Agents</h3>
                    <p id="activeAgents">0 / 7 agents</p>
                </div>
                <div class="status-card">
                    <h3>API Status</h3>
                    <p id="apiStatus"><span class="status-indicator status-warning"></span>Connecting...</p>
                </div>
            </div>
        </div>

        <div class="progress-section" id="progressSection" style="display: none;">
            <h3>Analysis Progress</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="agent-status" id="agentStatus">
                <div class="agent-card">
                    <h4>Fundamental</h4>
                    <p>Ready</p>
                </div>
                <div class="agent-card">
                    <h4>Sentiment</h4>
                    <p>Ready</p>
                </div>
                <div class="agent-card">
                    <h4>News</h4>
                    <p>Ready</p>
                </div>
                <div class="agent-card">
                    <h4>Technical</h4>
                    <p>Ready</p>
                </div>
                <div class="agent-card">
                    <h4>Bullish</h4>
                    <p>Ready</p>
                </div>
                <div class="agent-card">
                    <h4>Bearish</h4>
                    <p>Ready</p>
                </div>
                <div class="agent-card">
                    <h4>Trader</h4>
                    <p>Ready</p>
                </div>
            </div>
        </div>

        <div class="results-section" id="resultsSection" style="display: none;">
            <h2>📊 Analysis Results</h2>
            <div id="results"></div>
        </div>

        <div class="history-section">
            <h2>📈 Analysis History</h2>
            <div class="history-controls">
                <button onclick="loadAnalysisHistory()" class="btn">🔄 Refresh History</button>
            </div>
            <div id="historyContainer" class="history-container">
                <div class="loading">Loading analysis history...</div>
            </div>
        </div>
    </div>

    <script>
        let currentAnalysisId = null;
        let analysisInterval = null;

        // Check system status on load
        window.onload = function() {
            checkSystemStatus();
            setInterval(checkSystemStatus, 30000); // Check every 30 seconds
            setupAutoComplete();
            // Load analysis history on startup
            loadAnalysisHistory();
        };

        function setSymbol(symbol) {
            document.getElementById('symbol').value = symbol;
            updateCompanyInfo(symbol);
            hideAutocomplete();
        }

        // Auto-complete functionality
        function setupAutoComplete() {
            const symbolInput = document.getElementById('symbol');
            const autocompleteDiv = document.getElementById('autocomplete');
            let searchTimeout;

            symbolInput.addEventListener('input', function() {
                const query = this.value.trim().toUpperCase();
                
                // Clear previous timeout
                if (searchTimeout) clearTimeout(searchTimeout);
                
                if (query.length === 0) {
                    hideAutocomplete();
                    document.getElementById('companyInfo').textContent = '';
                    return;
                }

                // Update company info for exact matches
                updateCompanyInfo(query);

                // Debounce search
                searchTimeout = setTimeout(() => {
                    if (query.length >= 1) {
                        searchCompanies(query);
                    } else {
                        hideAutocomplete();
                    }
                }, 300);
            });

            symbolInput.addEventListener('blur', function() {
                // Hide autocomplete after a short delay to allow clicks
                setTimeout(hideAutocomplete, 200);
            });

            symbolInput.addEventListener('focus', function() {
                const query = this.value.trim().toUpperCase();
                if (query.length >= 1) {
                    searchCompanies(query);
                }
            });
        }

        async function updateCompanyInfo(symbol) {
            if (symbol.length === 0) {
                document.getElementById('companyInfo').textContent = '';
                return;
            }

            try {
                const response = await fetch(`/api/company-info/${symbol}`);
                const data = await response.json();
                
                if (data.found) {
                    document.getElementById('companyInfo').textContent = data.company_name;
                } else {
                    document.getElementById('companyInfo').textContent = '';
                }
            } catch (error) {
                document.getElementById('companyInfo').textContent = '';
            }
        }

        async function searchCompanies(query) {
            try {
                const response = await fetch(`/api/search-companies/${query}`);
                const data = await response.json();
                showAutocomplete(data.matches);
            } catch (error) {
                console.error('Search error:', error);
                hideAutocomplete();
            }
        }

        function showAutocomplete(matches) {
            const autocompleteDiv = document.getElementById('autocomplete');
            
            if (matches.length === 0) {
                hideAutocomplete();
                return;
            }

            autocompleteDiv.innerHTML = '';
            matches.forEach(match => {
                const item = document.createElement('div');
                item.className = 'autocomplete-item';
                item.innerHTML = `
                    <div class="autocomplete-symbol">${match.symbol}</div>
                    <div class="autocomplete-company">${match.company_name}</div>
                `;
                item.onclick = () => selectSymbol(match.symbol);
                autocompleteDiv.appendChild(item);
            });

            autocompleteDiv.style.display = 'block';
        }

        function hideAutocomplete() {
            document.getElementById('autocomplete').style.display = 'none';
        }

        function selectSymbol(symbol) {
            document.getElementById('symbol').value = symbol;
            updateCompanyInfo(symbol);
            hideAutocomplete();
        }

        // Analysis History functionality
        async function loadAnalysisHistory() {
            const historyContainer = document.getElementById('historyContainer');
            historyContainer.innerHTML = '<div class="loading">Loading analysis history...</div>';

            try {
                const response = await fetch('/api/history');
                const data = await response.json();
                
                if (data.analyses && data.analyses.length > 0) {
                    displayAnalysisHistory(data.analyses);
                } else {
                    historyContainer.innerHTML = '<div class="loading">No analysis history found. Run some analyses to see them here!</div>';
                }
            } catch (error) {
                console.error('History loading error:', error);
                historyContainer.innerHTML = '<div class="error">Failed to load analysis history</div>';
            }
        }

        function displayAnalysisHistory(analyses) {
            const historyContainer = document.getElementById('historyContainer');
            historyContainer.innerHTML = '';

            analyses.forEach(analysis => {
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';
                
                const decision = analysis.decision || 'Unknown';
                const decisionClass = decision.toLowerCase().includes('buy') ? 'buy' : 
                                    decision.toLowerCase().includes('sell') ? 'sell' : 
                                    decision.toLowerCase().includes('hold') ? 'hold' : '';
                
                const completedAt = analysis.completed_at ? new Date(analysis.completed_at) : null;
                const timeStr = completedAt ? completedAt.toLocaleString() : 'Unknown time';
                const duration = analysis.duration_formatted || 'Unknown duration';
                
                historyItem.innerHTML = `
                    <div class="history-header">
                        <div class="history-symbol">${analysis.symbol}</div>
                        <div class="history-decision ${decisionClass}">${decision}</div>
                    </div>
                    <div class="history-meta">
                        <div class="history-date">📅 ${timeStr}</div>
                        <div>📊 Analysis Date: ${analysis.date}</div>
                        <div class="history-duration">⏱️ Duration: ${duration}</div>
                    </div>
                    <div class="history-actions">
                        <button class="download-btn" onclick="downloadAnalysis('${analysis.analysis_id}', '${analysis.symbol}')">
                            📄 Text
                        </button>
                        <button class="download-btn pdf-btn" onclick="downloadAnalysisPDF('${analysis.analysis_id}', '${analysis.symbol}')">
                            📑 PDF
                        </button>
                    </div>
                `;

                historyItem.onclick = () => viewHistoryDetails(analysis);
                historyContainer.appendChild(historyItem);
            });
        }

        function viewHistoryDetails(analysis) {
            // Re-run analysis for this symbol and date
            document.getElementById('symbol').value = analysis.symbol;
            document.getElementById('date').value = analysis.date;
            updateCompanyInfo(analysis.symbol);
            
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            
            // Optionally show a message
            const analysisProgress = document.getElementById('analysisProgress');
            if (analysisProgress) {
                analysisProgress.textContent = `Click "Start Analysis" to re-run analysis for ${analysis.symbol}`;
            }
        }

        async function checkSystemStatus() {
            console.log('🔍 Checking system status...');
            try {
                const response = await fetch('/api/health');
                console.log('📡 API Response:', response.status);
                const data = await response.json();
                console.log('📊 API Data:', data);
                
                if (data.status === 'healthy') {
                    console.log('✅ System is healthy, updating UI');
                    document.getElementById('systemStatus').innerHTML = 
                        '<span class="status-indicator status-healthy"></span>System Healthy';
                    document.getElementById('apiStatus').innerHTML = 
                        '<span class="status-indicator status-healthy"></span>API Connected';
                } else {
                    console.log('❌ System not healthy:', data.status);
                    document.getElementById('systemStatus').innerHTML = 
                        '<span class="status-indicator status-error"></span>System Error';
                    document.getElementById('apiStatus').innerHTML = 
                        '<span class="status-indicator status-error"></span>API Error';
                }
            } catch (error) {
                console.error('💥 API Error:', error);
                document.getElementById('systemStatus').innerHTML = 
                    '<span class="status-indicator status-error"></span>Connection Failed';
                document.getElementById('apiStatus').innerHTML = 
                    '<span class="status-indicator status-error"></span>API Offline';
            }
        }

        let progressCheckInterval = null;

        async function startAnalysis(event) {
            event.preventDefault();
            
            const symbol = document.getElementById('symbol').value.toUpperCase();
            const date = document.getElementById('date').value;
            
            if (!symbol) {
                alert('Please enter a stock symbol');
                return;
            }

            // Show progress section
            document.getElementById('progressSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';
            
            // Update UI
            const analyzeBtn = document.getElementById('analyzeBtn');
            analyzeBtn.disabled = true;
            analyzeBtn.textContent = '🔄 Analyzing...';
            analyzeBtn.classList.add('pulse');
            
            document.getElementById('analysisProgress').textContent = `Analyzing ${symbol}...`;
            document.getElementById('activeAgents').textContent = 'Initializing agents...';
            
            // Reset progress
            document.getElementById('progressFill').style.width = '5%';
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ symbol, date }),
                });
                
                // Check if response is actually JSON
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    const responseText = await response.text();
                    showError(`Server returned non-JSON response: ${responseText.substring(0, 200)}...`);
                    return;
                }
                
                const result = await response.json();
                
                if (result.error) {
                    showError(result.message || 'Analysis failed');
                } else if (result.status === 'started') {
                    // Store analysis ID and start progress tracking for async analysis
                    currentAnalysisId = result.analysis_id;
                    console.log(`🚀 Analysis started with ID: ${currentAnalysisId}`);
                    startRealTimeProgress();
                } else {
                    // Handle synchronous response - still start progress tracking to show intermediate steps
                    currentAnalysisId = result.analysis_id;
                    console.log(`📊 Analysis completed with ID: ${currentAnalysisId}`);
                    
                    // Start progress tracking briefly to show any intermediate states
                    startRealTimeProgress();
                    
                    // Show results after a brief delay to allow progress to be seen
                    setTimeout(() => {
                        if (progressCheckInterval) {
                            clearInterval(progressCheckInterval);
                            progressCheckInterval = null;
                        }
                        showResults(result);
                        
                        // Reset button
                        const analyzeBtn = document.getElementById('analyzeBtn');
                        analyzeBtn.disabled = false;
                        analyzeBtn.textContent = '🔍 Start Analysis';
                        analyzeBtn.classList.remove('pulse');
                    }, 3000); // Wait 3 seconds to show progress
                }
            } catch (error) {
                console.error('Analysis error:', error);
                if (error.message.includes('Unexpected token') || error.message.includes('JSON') || error.message.includes('Expecting value')) {
                    showError('Server returned invalid response. The API service may be starting up or experiencing issues. Please wait a moment and try again.');
                } else {
                    showError('Network error: ' + error.message);
                }
                
                // Reset button on error
                const analyzeBtn = document.getElementById('analyzeBtn');
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = '🔍 Start Analysis';
                analyzeBtn.classList.remove('pulse');
                
                // Stop progress tracking on error
                if (progressCheckInterval) {
                    clearInterval(progressCheckInterval);
                    progressCheckInterval = null;
                }
            }
        }

        function startRealTimeProgress() {
            if (!currentAnalysisId) {
                console.log('❌ No analysis ID available for progress tracking');
                return;
            }
            
            // Poll for real progress every 2 seconds
            progressCheckInterval = setInterval(async () => {
                try {
                    console.log(`🔄 Checking progress for analysis: ${currentAnalysisId}`);
                    const response = await fetch(`/api/progress/${currentAnalysisId}`);
                    
                    if (response.ok) {
                        // Check if response is actually JSON
                        const contentType = response.headers.get('content-type');
                        if (!contentType || !contentType.includes('application/json')) {
                            console.warn('⚠️ Progress endpoint returned non-JSON response');
                            return;
                        }
                        
                        const progressData = await response.json();
                        console.log('📊 Progress data:', progressData);
                        
                        // Update progress bar
                        const progress = progressData.progress || 0;
                        document.getElementById('progressFill').style.width = progress + '%';
                        
                        // Update status messages
                        const status = progressData.status || 'unknown';
                        const currentAgent = progressData.current_agent || 'System';
                        const messages = progressData.messages || [];
                        
                        document.getElementById('analysisProgress').textContent = 
                            messages.length > 0 ? messages[messages.length - 1] : `Status: ${status}`;
                        document.getElementById('activeAgents').textContent = `${currentAgent} (${progress}%)`;
                        
                        // Update individual agent cards based on progress
                        updateAgentCards(progress, currentAgent);
                        
                        // Stop polling when complete
                        if (status === 'completed' || progress >= 100) {
                            console.log('✅ Analysis completed, stopping progress polling');
                            clearInterval(progressCheckInterval);
                            progressCheckInterval = null;
                            
                            // Update final status
                            document.getElementById('analysisProgress').textContent = '✅ Analysis Complete';
                            document.getElementById('activeAgents').textContent = 'All agents finished';
                            document.getElementById('progressFill').style.width = '100%';
                            
                            // Show results from progress data
                            if (progressData.result && progressData.decision) {
                                const result = {
                                    analysis_id: currentAnalysisId,
                                    symbol: progressData.symbol,
                                    analysis_date: progressData.date,
                                    decision: progressData.decision,
                                    result: progressData.result,
                                    timestamp: progressData.completed_at,
                                    status: 'completed'
                                };
                                showResults(result);
                            }
                            
                            // Reset button
                            const analyzeBtn = document.getElementById('analyzeBtn');
                            analyzeBtn.disabled = false;
                            analyzeBtn.textContent = '🔍 Start Analysis';
                            analyzeBtn.classList.remove('pulse');
                        }
                    } else {
                        console.log('⚠️ Progress endpoint not responding, using fallback');
                        // Keep existing fake progress as fallback
                        useFallbackProgress();
                    }
                } catch (error) {
                    console.error('❌ Progress polling error:', error);
                    // Keep existing fake progress as fallback
                    useFallbackProgress();
                }
            }, 2000); // Update every 2 seconds
        }
        
        function updateAgentCards(progress, currentAgent) {
            // Reset all cards
            const agentCards = document.querySelectorAll('.agent-card');
            agentCards.forEach(card => {
                card.classList.remove('active');
                card.querySelector('p').textContent = 'Ready';
            });
            
            // Highlight current active agent
            const agentNames = {
                'Fundamental': 'Fundamental',
                'Sentiment': 'Sentiment', 
                'News': 'News',
                'Technical': 'Technical',
                'Bullish': 'Bullish',
                'Bearish': 'Bearish',
                'Trading Decision Maker': 'Trader',
                'Multi-Agent System': 'Fundamental' // Default to first agent
            };
            
            const cardName = agentNames[currentAgent] || 'Fundamental';
            const activeCard = Array.from(agentCards).find(card => 
                card.querySelector('h4').textContent === cardName
            );
            
            if (activeCard) {
                activeCard.classList.add('active');
                activeCard.querySelector('p').textContent = 'Working...';
            }
        }
        
        function useFallbackProgress() {
            // Fallback fake progress if real progress fails
            let progressStep = parseInt(document.getElementById('progressFill').style.width) || 10;
            const maxProgress = 95;
            
            if (progressStep < maxProgress) {
                progressStep += Math.random() * 3; // Slower increment
                if (progressStep > maxProgress) progressStep = maxProgress;
                
                document.getElementById('progressFill').style.width = progressStep + '%';
                
                // Generic status messages
                if (progressStep < 30) {
                    document.getElementById('analysisProgress').textContent = '🚀 Analysis in progress...';
                } else if (progressStep < 60) {
                    document.getElementById('analysisProgress').textContent = '📊 Agents analyzing data...';
                } else if (progressStep < 85) {
                    document.getElementById('analysisProgress').textContent = '🤔 Final decision making...';
                }
            }
        }


        function showResults(result) {
            document.getElementById('resultsSection').style.display = 'block';
            
            let decisionClass = 'decision-card';
            if (result.decision && result.decision.toLowerCase().includes('sell')) {
                decisionClass += ' sell';
            } else if (result.decision && result.decision.toLowerCase().includes('hold')) {
                decisionClass += ' hold';
            }
            
            const resultsHtml = `
                <div class="${decisionClass}">
                    <h3>🎯 Trading Decision</h3>
                    <div style="font-size: 1.5em; margin-top: 10px;">
                        ${result.decision || 'Analysis Complete'}
                    </div>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <strong>Symbol:</strong> ${result.symbol}<br>
                    <strong>Analysis Date:</strong> ${result.analysis_date}<br>
                    <strong>Completed:</strong> ${new Date(result.timestamp).toLocaleString()}<br>
                    <strong>Status:</strong> ${result.status}
                </div>
                
                <h3>📋 Detailed Analysis</h3>
                <div class="analysis-details">${result.result || 'No detailed results available'}</div>
            `;
            
            document.getElementById('results').innerHTML = resultsHtml;
            document.getElementById('analysisProgress').textContent = 'Analysis Complete';
        }

        function showError(message) {
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('results').innerHTML = `
                <div class="error">
                    <h3>❌ Analysis Error</h3>
                    <p>${message}</p>
                </div>
            `;
            document.getElementById('analysisProgress').textContent = 'Analysis Failed';
            document.getElementById('activeAgents').textContent = '0 / 7 agents';
        }

        // Download analysis summary (text)
        function downloadAnalysis(analysisId, symbol) {
            event.stopPropagation(); // Prevent triggering the history item click
            
            // Create download link
            const downloadUrl = `/api/download/${analysisId}`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = `analysis_${symbol}_${analysisId}.txt`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        // Download analysis summary (PDF)
        function downloadAnalysisPDF(analysisId, symbol) {
            event.stopPropagation(); // Prevent triggering the history item click
            
            // Create download link
            const downloadUrl = `/api/download/${analysisId}/pdf`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = `analysis_${symbol}_${analysisId}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard page"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template_string(HTML_TEMPLATE, current_date=current_date)

@app.route('/api/health')
def health_proxy():
    """Proxy health check to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/health", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/api/analyze', methods=['POST'])
def analyze_proxy():
    """Proxy analysis request to TradingAgents API"""
    try:
        data = request.get_json()
        
        # Forward request to TradingAgents API
        response = requests.post(
            f"{TRADINGAGENTS_API_URL}/api/analyze",
            json=data,
            timeout=600  # 10 minutes timeout
        )
        
        return response.json(), response.status_code
        
    except requests.exceptions.Timeout:
        return {
            "error": "Analysis timeout", 
            "message": "Analysis took longer than 10 minutes. The system may still be processing."
        }, 408
    except Exception as e:
        return {"error": "Analysis failed", "message": str(e)}, 500

@app.route('/api/progress/<analysis_id>')
def progress_proxy(analysis_id):
    """Proxy progress request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/progress/{analysis_id}", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "Progress check failed", "message": str(e)}, 500

@app.route('/api/progress')
def all_progress_proxy():
    """Proxy all progress request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/progress", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "Progress check failed", "message": str(e)}, 500

@app.route('/api/config')
def config_proxy():
    """Proxy config request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/config", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "Config failed", "message": str(e)}, 500

@app.route('/api/agents')
def agents_proxy():
    """Proxy agents request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/agents", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "Agents failed", "message": str(e)}, 500

@app.route('/api/history')
def history_proxy():
    """Proxy history request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/history", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "History failed", "message": str(e)}, 500

@app.route('/api/company-info/<symbol>')
def company_info_proxy(symbol):
    """Proxy company info request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/company-info/{symbol}", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "Company info failed", "message": str(e)}, 500

@app.route('/api/search-companies/<query>')
def search_companies_proxy(query):
    """Proxy company search request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/search-companies/{query}", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "Company search failed", "message": str(e)}, 500

@app.route('/api/download/<analysis_id>')
def download_analysis_proxy(analysis_id):
    """Proxy download request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/download/{analysis_id}", timeout=30)
        
        # Forward the file download response
        from flask import Response
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        return {"error": "Download failed", "message": str(e)}, 500

@app.route('/api/download/<analysis_id>/pdf')
def download_analysis_pdf_proxy(analysis_id):
    """Proxy PDF download request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/api/download/{analysis_id}/pdf", timeout=30)
        
        # Forward the PDF download response
        from flask import Response
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        return {"error": "PDF download failed", "message": str(e)}, 500

if __name__ == "__main__":
    print(f"🚀 Starting TradingAgents Dashboard on port {DASHBOARD_PORT}...")
    print(f"📡 Connecting to TradingAgents API at: {TRADINGAGENTS_API_URL}")
    print(f"🌐 Dashboard will be available at: http://localhost:{DASHBOARD_PORT}")
    
    app.run(host="0.0.0.0", port=DASHBOARD_PORT, debug=True)