#!/usr/bin/env python3
"""
TradingAgents Web API - Multi-Agent LLM Financial Trading Framework
Deploy the TradingAgents framework as a REST API service
"""

import os
import logging
from flask import Flask, jsonify, request
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global variable to store trading agents instance
ta_graph = None

def initialize_trading_agents():
    """Initialize TradingAgents with environment configuration"""
    global ta_graph
    
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
        
        # Create configuration from environment variables
        config = DEFAULT_CONFIG.copy()
        
        # Configure LLM provider and models
        llm_provider = os.getenv("LLM_PROVIDER", "openai")
        config["llm_provider"] = llm_provider
        
        if llm_provider == "openai":
            config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", "gpt-4o-mini")
            config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", "gpt-4o-mini")
        elif llm_provider == "google":
            config["backend_url"] = "https://generativelanguage.googleapis.com/v1"
            config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", "gemini-2.0-flash")
            config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", "gemini-2.0-flash")
        
        # Configure debate rounds and tools
        config["max_debate_rounds"] = int(os.getenv("MAX_DEBATE_ROUNDS", "1"))
        config["online_tools"] = os.getenv("ONLINE_TOOLS", "true").lower() == "true"
        
        # Initialize TradingAgents
        ta_graph = TradingAgentsGraph(debug=True, config=config)
        logger.info(f"✅ TradingAgents initialized with {llm_provider} provider")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize TradingAgents: {e}")
        traceback.print_exc()
        return False

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    global ta_graph
    
    return jsonify({
        "status": "healthy" if ta_graph is not None else "initializing",
        "timestamp": datetime.now().isoformat(),
        "service": "tradingagents-api",
        "version": "1.0.0",
        "agents_ready": ta_graph is not None,
        "required_apis": {
            "openai_key": bool(os.getenv("OPENAI_API_KEY")),
            "finnhub_key": bool(os.getenv("FINNHUB_API_KEY")),
            "google_api_key": bool(os.getenv("GOOGLE_API_KEY"))
        }
    })

@app.route('/')
def index():
    """Main endpoint with API information"""
    return jsonify({
        "message": "TradingAgents Multi-Agent LLM Financial Trading Framework",
        "version": "1.0.0",
        "description": "AI-powered trading system with specialized analyst, researcher, and trader agents",
        "endpoints": {
            "/health": "Health check and system status",
            "/analyze": "Analyze a stock with multi-agent decision making",
            "/config": "Current system configuration",
            "/agents": "List available agent types"
        },
        "documentation": "https://github.com/TauricResearch/TradingAgents",
        "agents": {
            "analysts": ["Fundamental", "Sentiment", "News", "Technical"],
            "researchers": ["Bullish", "Bearish"], 
            "trader": "Trading Decision Maker",
            "risk_management": "Portfolio Risk Manager"
        }
    })

@app.route('/analyze', methods=['POST'])
def analyze_stock():
    """Analyze a stock using the multi-agent system"""
    global ta_graph
    
    if ta_graph is None:
        return jsonify({
            "error": "TradingAgents not initialized",
            "message": "System is still starting up. Please try again in a few moments."
        }), 503
    
    try:
        # Get parameters from request
        data = request.get_json() or {}
        symbol = data.get('symbol', request.args.get('symbol', 'AAPL'))
        date = data.get('date', request.args.get('date', datetime.now().strftime('%Y-%m-%d')))
        
        logger.info(f"🔍 Analyzing {symbol} for date {date}")
        
        # Run the multi-agent analysis
        result, decision = ta_graph.propagate(symbol, date)
        
        # Convert result and decision to JSON-serializable format
        serializable_result = str(result) if result else None
        serializable_decision = str(decision) if decision else None
        
        return jsonify({
            "symbol": symbol,
            "analysis_date": date,
            "decision": serializable_decision,
            "result": serializable_result,
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        })
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        return jsonify({
            "error": "Analysis failed",
            "message": str(e),
            "symbol": symbol,
            "date": date
        }), 500

@app.route('/config')
def get_config():
    """Get current system configuration"""
    global ta_graph
    
    return jsonify({
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "deep_think_llm": os.getenv("DEEP_THINK_LLM", "gpt-4o-mini"),
        "quick_think_llm": os.getenv("QUICK_THINK_LLM", "gpt-4o-mini"),
        "max_debate_rounds": int(os.getenv("MAX_DEBATE_ROUNDS", "1")),
        "online_tools": os.getenv("ONLINE_TOOLS", "true").lower() == "true",
        "agents_initialized": ta_graph is not None,
        "required_env_vars": [
            "OPENAI_API_KEY", 
            "FINNHUB_API_KEY",
            "GOOGLE_API_KEY (if using Google models)"
        ]
    })

@app.route('/agents')
def list_agents():
    """List all available agent types and their roles"""
    return jsonify({
        "analyst_team": {
            "fundamental_analyst": "Evaluates company financials and performance metrics",
            "sentiment_analyst": "Analyzes social media and public sentiment",
            "news_analyst": "Monitors global news and macroeconomic indicators", 
            "technical_analyst": "Uses technical indicators like MACD and RSI"
        },
        "researcher_team": {
            "bullish_researchers": "Find reasons to buy/hold positions",
            "bearish_researchers": "Find reasons to sell/short positions"
        },
        "decision_makers": {
            "trader_agent": "Makes final trading decisions based on all analysis",
            "risk_manager": "Evaluates portfolio risk and approves/rejects trades",
            "portfolio_manager": "Final approval for trade execution"
        }
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    debug_mode = os.getenv("FLASK_ENV") == "development"
    
    logger.info("🚀 Starting TradingAgents API server...")
    
    # Initialize TradingAgents on startup
    if not initialize_trading_agents():
        logger.error("⚠️ TradingAgents initialization failed, but starting server anyway")
    
    logger.info(f"📡 TradingAgents API running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)