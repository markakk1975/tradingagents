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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# Global progress tracking
analysis_progress = {}

def clean_analysis_result(result):
    """Extract clean, readable text from LangChain analysis results"""
    if not result:
        return None
    
    try:
        # If it's a dictionary with messages
        if isinstance(result, dict) and 'messages' in result:
            clean_text = []
            
            # Extract content from messages
            if result.get('messages'):
                for msg in result['messages']:
                    if hasattr(msg, 'content'):
                        clean_text.append(msg.content)
                    elif isinstance(msg, dict) and 'content' in msg:
                        clean_text.append(msg['content'])
            
            # Add other relevant fields
            for key in ['market_report', 'sentiment_report', 'news_report', 'fundamentals_report']:
                if key in result and result[key]:
                    clean_text.append(f"\n\n## {key.replace('_', ' ').title()}\n{result[key]}")
            
            # Add investment debate if available
            if 'investment_debate_state' in result and result['investment_debate_state']:
                debate = result['investment_debate_state']
                if isinstance(debate, dict) and 'judge_decision' in debate:
                    clean_text.append(f"\n\n## Investment Decision\n{debate['judge_decision']}")
            
            return '\n'.join(clean_text)
        
        # If it's just a string, return as-is
        elif isinstance(result, str):
            return result
        
        # Otherwise, try to extract meaningful content
        else:
            # Convert to string but try to extract content if it has it
            if hasattr(result, 'content'):
                return result.content
            else:
                return str(result)
                
    except Exception as e:
        logger.warning(f"Failed to clean analysis result: {e}")
        return str(result)

def clean_decision_result(decision):
    """Extract clean decision text from LangChain decision objects"""
    if not decision:
        return None
    
    try:
        # If it has content attribute, extract it
        if hasattr(decision, 'content'):
            content = decision.content
            # Extract just the final decision if it contains "FINAL TRANSACTION PROPOSAL"
            if "FINAL TRANSACTION PROPOSAL" in content:
                lines = content.split('\n')
                for line in lines:
                    if "FINAL TRANSACTION PROPOSAL" in line:
                        return line.split(":")[-1].strip()
            return content
        
        # If it's a string, look for the decision
        elif isinstance(decision, str):
            if "FINAL TRANSACTION PROPOSAL" in decision:
                lines = decision.split('\n')
                for line in lines:
                    if "FINAL TRANSACTION PROPOSAL" in line:
                        return line.split(":")[-1].strip()
            return decision
        
        # Otherwise convert to string
        else:
            return str(decision)
            
    except Exception as e:
        logger.warning(f"Failed to clean decision result: {e}")
        return str(decision)

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

@app.route('/api/health')
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

@app.route('/api/analyze', methods=['POST'])
def analyze_stock():
    """Analyze a stock using the multi-agent system"""
    global ta_graph
    
    if ta_graph is None:
        # Try to initialize again
        logger.info("🔄 Attempting to re-initialize TradingAgents...")
        if not initialize_trading_agents():
            return jsonify({
                "error": "TradingAgents initialization failed",
                "message": "System cannot be initialized. Please check server logs and try again later."
            }), 503
        
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
        
        # Initialize progress tracking for this analysis
        analysis_id = f"{symbol}_{date}_{datetime.now().strftime('%H%M%S')}"
        analysis_progress[analysis_id] = {
            "symbol": symbol,
            "date": date,
            "status": "starting",
            "progress": 0,
            "current_agent": "Initializing",
            "agents_completed": [],
            "started_at": datetime.now().isoformat(),
            "messages": ["🚀 Starting multi-agent analysis..."]
        }
        
        # Update progress - Starting analysis
        analysis_progress[analysis_id]["status"] = "analyzing"
        analysis_progress[analysis_id]["progress"] = 10
        analysis_progress[analysis_id]["current_agent"] = "Multi-Agent System"
        analysis_progress[analysis_id]["messages"].append(f"📊 Initializing analysis for {symbol}")
        
        # Run the multi-agent analysis synchronously with detailed progress
        logger.info(f"📈 Running multi-agent propagation for {symbol}")
        analysis_progress[analysis_id]["progress"] = 25
        analysis_progress[analysis_id]["current_agent"] = "Fundamental Analyst"
        analysis_progress[analysis_id]["messages"].append("📊 Fundamental analyst working...")
        
        # Simulate some progress updates during analysis
        import time
        time.sleep(1)  # Brief delay to show progress
        analysis_progress[analysis_id]["progress"] = 40
        analysis_progress[analysis_id]["current_agent"] = "Technical Analyst"
        analysis_progress[analysis_id]["messages"].append("📈 Technical analysis in progress...")
        
        time.sleep(0.5)  # Another brief delay
        analysis_progress[analysis_id]["progress"] = 60
        analysis_progress[analysis_id]["current_agent"] = "Sentiment Analyst"
        analysis_progress[analysis_id]["messages"].append("😊 Sentiment analysis running...")
        
        # Check if we have valid API keys before starting analysis
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key or openai_key == "test_key_demo_only":
            analysis_progress[analysis_id]["status"] = "failed"
            analysis_progress[analysis_id]["messages"].append("❌ Invalid OpenAI API key - please configure a valid API key")
            return jsonify({
                "error": "Configuration error",
                "message": "OpenAI API key not configured properly. Please set a valid OPENAI_API_KEY.",
                "analysis_id": analysis_id,
                "symbol": symbol,
                "date": date
            }), 400
        
        # Run analysis with timeout protection using threading
        import threading
        import queue
        
        result_queue = queue.Queue()
        analysis_error = None
        
        def run_analysis():
            try:
                logger.info(f"🚀 Starting ta_graph.propagate for {symbol} on {date}")
                start_time = time.time()
                result, decision = ta_graph.propagate(symbol, date)
                end_time = time.time()
                logger.info(f"✅ Analysis completed in {end_time - start_time:.2f} seconds")
                result_queue.put(('success', result, decision))
            except Exception as e:
                logger.error(f"❌ Analysis failed: {e}")
                result_queue.put(('error', str(e), None))
        
        # Start analysis in background thread
        analysis_thread = threading.Thread(target=run_analysis)
        analysis_thread.daemon = True
        analysis_thread.start()
        
        # Wait for result with timeout (increased for complex analyses)
        # Check progress every 15 seconds and update user
        total_timeout = 120  # 2 minutes total
        check_interval = 15  # seconds
        elapsed = 0
        
        while elapsed < total_timeout and analysis_thread.is_alive():
            analysis_thread.join(timeout=check_interval)
            elapsed += check_interval
            
            if analysis_thread.is_alive() and elapsed < total_timeout:
                # Still running, update progress
                analysis_progress[analysis_id]["messages"].append(f"🔄 Analysis still running... ({elapsed}s elapsed)")
                logger.info(f"⏳ Analysis still running for {symbol} after {elapsed}s")
        
        if analysis_thread.is_alive():
            # Analysis is still running, it timed out
            analysis_progress[analysis_id]["status"] = "timeout"
            analysis_progress[analysis_id]["messages"].append("⏰ Analysis timed out after 2 minutes")
            return jsonify({
                "error": "Analysis timeout", 
                "message": "Analysis took too long and was cancelled",
                "analysis_id": analysis_id,
                "symbol": symbol,
                "date": date
            }), 408
        
        # Get result from queue
        try:
            status, result, decision = result_queue.get_nowait()
            if status == 'error':
                raise Exception(result)
        except queue.Empty:
            analysis_progress[analysis_id]["status"] = "failed"
            analysis_progress[analysis_id]["messages"].append("❌ Analysis failed unexpectedly")
            return jsonify({
                "error": "Analysis failed",
                "message": "Analysis completed but no result was returned",
                "analysis_id": analysis_id,
                "symbol": symbol,
                "date": date
            }), 500
        
        # Update progress - Analysis complete
        analysis_progress[analysis_id]["status"] = "completed"
        analysis_progress[analysis_id]["progress"] = 100
        analysis_progress[analysis_id]["current_agent"] = "Completed"
        analysis_progress[analysis_id]["completed_at"] = datetime.now().isoformat()
        analysis_progress[analysis_id]["messages"].append("✅ Analysis completed successfully!")
        
        # Convert result and decision to clean, readable format
        serializable_result = clean_analysis_result(result)
        serializable_decision = clean_decision_result(decision)
        
        # Store results in progress for dashboard access
        analysis_progress[analysis_id]["result"] = serializable_result
        analysis_progress[analysis_id]["decision"] = serializable_decision
        
        return jsonify({
            "analysis_id": analysis_id,
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

@app.route('/api/progress/<analysis_id>')
def get_analysis_progress(analysis_id):
    """Get real-time analysis progress"""
    if analysis_id not in analysis_progress:
        return jsonify({
            "error": "Analysis not found",
            "analysis_id": analysis_id
        }), 404
    
    return jsonify(analysis_progress[analysis_id])

@app.route('/api/progress')
def list_active_analyses():
    """List all active and recent analyses"""
    return jsonify({
        "active_analyses": list(analysis_progress.keys()),
        "total_count": len(analysis_progress),
        "analyses": analysis_progress
    })

@app.route('/api/config')
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

@app.route('/api/history')
def analysis_history():
    """Get analysis history with completed analyses"""
    try:
        completed_analyses = []
        
        for analysis_id, data in analysis_progress.items():
            if data.get('status') == 'completed':
                completed_analyses.append({
                    'analysis_id': analysis_id,
                    'symbol': data.get('symbol'),
                    'date': data.get('date'),
                    'decision': data.get('decision', 'Unknown'),
                    'started_at': data.get('started_at'),
                    'completed_at': data.get('completed_at'),
                    'messages': data.get('messages', [])
                })
        
        # Sort by completion time (most recent first)
        completed_analyses.sort(key=lambda x: x.get('completed_at', ''), reverse=True)
        
        # If no completed analyses yet, return sample data to show how it works
        if not completed_analyses:
            sample_analyses = [
                {
                    'analysis_id': 'sample_001',
                    'symbol': 'AAPL',
                    'date': '2025-08-27',
                    'decision': 'BUY',
                    'started_at': '2025-08-27T10:00:00',
                    'completed_at': '2025-08-27T10:05:00',
                    'messages': ['Sample analysis - run a real analysis to see your history']
                }
            ]
            return jsonify({
                'total_count': len(sample_analyses),
                'analyses': sample_analyses,
                'is_sample': True
            })
        
        return jsonify({
            'total_count': len(completed_analyses),
            'analyses': completed_analyses[:20]  # Limit to last 20 analyses
        })
        
    except Exception as e:
        logger.error(f"❌ History endpoint error: {e}")
        return jsonify({
            'error': 'Failed to retrieve history',
            'message': str(e),
            'total_count': 0,
            'analyses': []
        }), 500

@app.route('/api/company-info/<symbol>')
def get_company_info(symbol):
    """Get company name and info for a stock symbol"""
    # Stock symbol to company name mapping
    company_names = {
        'AAPL': 'Apple Inc.',
        'GOOGL': 'Alphabet Inc.',
        'GOOG': 'Alphabet Inc.',
        'MSFT': 'Microsoft Corporation',
        'AMZN': 'Amazon.com Inc.',
        'TSLA': 'Tesla Inc.',
        'META': 'Meta Platforms Inc.',
        'NVDA': 'NVIDIA Corporation',
        'NFLX': 'Netflix Inc.',
        'ADBE': 'Adobe Inc.',
        'CRM': 'Salesforce Inc.',
        'ORCL': 'Oracle Corporation',
        'INTC': 'Intel Corporation',
        'AMD': 'Advanced Micro Devices Inc.',
        'PYPL': 'PayPal Holdings Inc.',
        'UBER': 'Uber Technologies Inc.',
        'SPOT': 'Spotify Technology S.A.',
        'SQ': 'Block Inc.',
        'ROKU': 'Roku Inc.',
        'ZOOM': 'Zoom Video Communications Inc.',
        'SHOP': 'Shopify Inc.',
        'TWTR': 'Twitter Inc.',
        'SNAP': 'Snap Inc.',
        'PINS': 'Pinterest Inc.',
        'DOCU': 'DocuSign Inc.',
        'WORK': 'Slack Technologies Inc.',
        'PLTR': 'Palantir Technologies Inc.',
        'SNOW': 'Snowflake Inc.',
        'CRWD': 'CrowdStrike Holdings Inc.',
        'ZM': 'Zoom Video Communications Inc.',
        'TEAM': 'Atlassian Corporation',
        'NOW': 'ServiceNow Inc.',
        'WDAY': 'Workday Inc.',
        'DDOG': 'Datadog Inc.',
        'NET': 'Cloudflare Inc.',
        'OKTA': 'Okta Inc.',
        'MDB': 'MongoDB Inc.',
        'SPLK': 'Splunk Inc.',
        'VEEV': 'Veeva Systems Inc.',
        'ZS': 'Zscaler Inc.'
    }
    
    symbol = symbol.upper()
    company_name = company_names.get(symbol)
    
    if company_name:
        return jsonify({
            'symbol': symbol,
            'company_name': company_name,
            'found': True
        })
    else:
        return jsonify({
            'symbol': symbol,
            'company_name': None,
            'found': False
        })

@app.route('/api/search-companies/<query>')
def search_companies(query):
    """Search companies by partial ticker symbol or name"""
    # Stock symbol to company name mapping (extended)
    company_names = {
        'AAPL': 'Apple Inc.',
        'GOOGL': 'Alphabet Inc.',
        'GOOG': 'Alphabet Inc.',
        'MSFT': 'Microsoft Corporation',
        'AMZN': 'Amazon.com Inc.',
        'TSLA': 'Tesla Inc.',
        'META': 'Meta Platforms Inc.',
        'NVDA': 'NVIDIA Corporation',
        'NFLX': 'Netflix Inc.',
        'ADBE': 'Adobe Inc.',
        'CRM': 'Salesforce Inc.',
        'ORCL': 'Oracle Corporation',
        'INTC': 'Intel Corporation',
        'AMD': 'Advanced Micro Devices Inc.',
        'PYPL': 'PayPal Holdings Inc.',
        'UBER': 'Uber Technologies Inc.',
        'SPOT': 'Spotify Technology S.A.',
        'SQ': 'Block Inc.',
        'ROKU': 'Roku Inc.',
        'ZOOM': 'Zoom Video Communications Inc.',
        'SHOP': 'Shopify Inc.',
        'TWTR': 'Twitter Inc.',
        'SNAP': 'Snap Inc.',
        'PINS': 'Pinterest Inc.',
        'DOCU': 'DocuSign Inc.',
        'WORK': 'Slack Technologies Inc.',
        'PLTR': 'Palantir Technologies Inc.',
        'SNOW': 'Snowflake Inc.',
        'CRWD': 'CrowdStrike Holdings Inc.',
        'ZM': 'Zoom Video Communications Inc.',
        'TEAM': 'Atlassian Corporation',
        'NOW': 'ServiceNow Inc.',
        'WDAY': 'Workday Inc.',
        'DDOG': 'Datadog Inc.',
        'NET': 'Cloudflare Inc.',
        'OKTA': 'Okta Inc.',
        'MDB': 'MongoDB Inc.',
        'SPLK': 'Splunk Inc.',
        'VEEV': 'Veeva Systems Inc.',
        'ZS': 'Zscaler Inc.'
    }
    
    query = query.upper()
    matches = []
    
    for symbol, company_name in company_names.items():
        if symbol.startswith(query) or query in company_name.upper():
            matches.append({
                'symbol': symbol,
                'company_name': company_name
            })
    
    # Sort by symbol length (exact matches first)
    matches.sort(key=lambda x: (len(x['symbol']), x['symbol']))
    
    return jsonify({
        'query': query,
        'matches': matches[:10]  # Limit to 10 results
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