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
                    <input type="text" id="symbol" placeholder="Stock Symbol (e.g. AAPL, TSLA, NVDA)" required>
                    <input type="date" id="date" value="{{ current_date }}">
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
    </div>

    <script>
        let currentAnalysisId = null;
        let analysisInterval = null;

        // Check system status on load
        window.onload = function() {
            checkSystemStatus();
            setInterval(checkSystemStatus, 30000); // Check every 30 seconds
        };

        function setSymbol(symbol) {
            document.getElementById('symbol').value = symbol;
        }

        async function checkSystemStatus() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                
                if (data.status === 'healthy') {
                    document.getElementById('systemStatus').innerHTML = 
                        '<span class="status-indicator status-healthy"></span>System Healthy';
                    document.getElementById('apiStatus').innerHTML = 
                        '<span class="status-indicator status-healthy"></span>API Connected';
                } else {
                    document.getElementById('systemStatus').innerHTML = 
                        '<span class="status-indicator status-error"></span>System Error';
                    document.getElementById('apiStatus').innerHTML = 
                        '<span class="status-indicator status-error"></span>API Error';
                }
            } catch (error) {
                document.getElementById('systemStatus').innerHTML = 
                    '<span class="status-indicator status-error"></span>Connection Failed';
                document.getElementById('apiStatus').innerHTML = 
                    '<span class="status-indicator status-error"></span>API Offline';
            }
        }

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
            document.getElementById('activeAgents').textContent = '7 / 7 agents active';
            
            // Reset progress
            document.getElementById('progressFill').style.width = '10%';
            
            // Simulate agent activation
            simulateAgentProgress();
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ symbol, date }),
                });
                
                const result = await response.json();
                
                if (result.error) {
                    showError(result.message || 'Analysis failed');
                } else {
                    showResults(result);
                }
            } catch (error) {
                showError('Network error: ' + error.message);
            } finally {
                // Reset button
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = '🔍 Start Analysis';
                analyzeBtn.classList.remove('pulse');
                document.getElementById('progressFill').style.width = '100%';
            }
        }

        function simulateAgentProgress() {
            const agents = [
                'Fundamental', 'Sentiment', 'News', 'Technical', 
                'Bullish', 'Bearish', 'Trader'
            ];
            
            let currentAgent = 0;
            const agentCards = document.querySelectorAll('.agent-card');
            
            const interval = setInterval(() => {
                if (currentAgent < agents.length) {
                    // Activate current agent
                    agentCards[currentAgent].classList.add('active');
                    agentCards[currentAgent].querySelector('p').textContent = 'Analyzing...';
                    
                    // Update progress
                    const progress = ((currentAgent + 1) / agents.length) * 80; // 80% for agents
                    document.getElementById('progressFill').style.width = progress + '%';
                    
                    currentAgent++;
                } else {
                    clearInterval(interval);
                    // Final processing
                    document.getElementById('progressFill').style.width = '95%';
                    agentCards.forEach(card => {
                        card.classList.remove('active');
                        card.querySelector('p').textContent = 'Complete';
                    });
                }
            }, 3000); // Each agent takes ~3 seconds
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
        response = requests.get(f"{TRADINGAGENTS_API_URL}/health", timeout=10)
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
            f"{TRADINGAGENTS_API_URL}/analyze",
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

@app.route('/api/config')
def config_proxy():
    """Proxy config request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/config", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "Config failed", "message": str(e)}, 500

@app.route('/api/agents')
def agents_proxy():
    """Proxy agents request to TradingAgents API"""
    try:
        response = requests.get(f"{TRADINGAGENTS_API_URL}/agents", timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": "Agents failed", "message": str(e)}, 500

if __name__ == "__main__":
    print(f"🚀 Starting TradingAgents Dashboard on port {DASHBOARD_PORT}...")
    print(f"📡 Connecting to TradingAgents API at: {TRADINGAGENTS_API_URL}")
    print(f"🌐 Dashboard will be available at: http://localhost:{DASHBOARD_PORT}")
    
    app.run(host="0.0.0.0", port=DASHBOARD_PORT, debug=True)