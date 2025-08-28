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
        total_timeout = 480  # 8 minutes total
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
            analysis_progress[analysis_id]["messages"].append("⏰ Analysis timed out after 8 minutes")
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
        completed_time = datetime.now()
        analysis_progress[analysis_id]["completed_at"] = completed_time.isoformat()
        
        # Calculate duration
        started_time = datetime.fromisoformat(analysis_progress[analysis_id]["started_at"])
        duration_seconds = (completed_time - started_time).total_seconds()
        analysis_progress[analysis_id]["duration_seconds"] = duration_seconds
        analysis_progress[analysis_id]["duration_formatted"] = f"{int(duration_seconds//60)}m {int(duration_seconds%60)}s"
        
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
                    'duration_seconds': data.get('duration_seconds', 0),
                    'duration_formatted': data.get('duration_formatted', 'Unknown'),
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
                    'duration_seconds': 300,
                    'duration_formatted': '5m 0s',
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
            'analyses': completed_analyses[:50]  # Limit to last 50 analyses
        })
        
    except Exception as e:
        logger.error(f"❌ History endpoint error: {e}")
        return jsonify({
            'error': 'Failed to retrieve history',
            'message': str(e),
            'total_count': 0,
            'analyses': []
        }), 500

@app.route('/api/download/<analysis_id>')
def download_analysis(analysis_id):
    """Download analysis summary as text file"""
    try:
        # Handle sample data
        if analysis_id == 'sample_001':
            data = {
                'analysis_id': 'sample_001',
                'symbol': 'AAPL',
                'date': '2025-08-27',
                'decision': 'BUY',
                'started_at': '2025-08-27T10:00:00',
                'completed_at': '2025-08-27T10:05:00',
                'duration_formatted': '5m 0s',
                'messages': ['Sample analysis - run a real analysis to see your history', 'This is a demo analysis summary'],
                'result': 'Sample analysis result: Apple Inc. shows strong fundamentals with positive technical indicators suggesting a BUY recommendation based on current market conditions.'
            }
        elif analysis_id not in analysis_progress:
            return jsonify({
                'error': 'Analysis not found',
                'analysis_id': analysis_id
            }), 404
        else:
            data = analysis_progress[analysis_id]
        
        # Create analysis summary text
        summary = f"""TradingAgents Analysis Summary
{'='*50}

Analysis ID: {analysis_id}
Symbol: {data.get('symbol', 'Unknown')}
Analysis Date: {data.get('date', 'Unknown')}
Started: {data.get('started_at', 'Unknown')}
Completed: {data.get('completed_at', 'Unknown')}
Duration: {data.get('duration_formatted', 'Unknown')}
Decision: {data.get('decision', 'Unknown')}

Analysis Progress:
{'-'*20}
"""
        
        # Add messages
        messages = data.get('messages', [])
        for i, message in enumerate(messages, 1):
            summary += f"{i}. {message}\n"
        
        # Add analysis result if available
        if 'result' in data and data['result']:
            summary += f"\nDetailed Analysis:\n{'-'*20}\n{data['result']}\n"
            
        # Return as downloadable file
        from flask import Response
        return Response(
            summary,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename=analysis_{data.get("symbol", "unknown")}_{analysis_id}.txt'}
        )
        
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        return jsonify({
            'error': 'Download failed',
            'message': str(e)
        }), 500

@app.route('/api/download/<analysis_id>/pdf')
def download_analysis_pdf(analysis_id):
    """Download analysis summary as PDF file"""
    try:
        # Handle sample data with comprehensive details
        if analysis_id == 'sample_001':
            data = {
                'analysis_id': 'sample_001',
                'symbol': 'AAPL',
                'company_name': 'Apple Inc.',
                'date': '2025-08-27',
                'decision': 'BUY',
                'started_at': '2025-08-27T10:00:00',
                'completed_at': '2025-08-27T10:05:00',
                'duration_formatted': '5m 0s',
                'messages': [
                    'Initializing multi-agent trading analysis system',
                    'Fundamental Analyst: Gathering financial metrics and company data',
                    'Technical Analyst: Analyzing price patterns and indicators (RSI: 45.2, MACD: Bullish)',
                    'Sentiment Analyst: Processing social media and news sentiment (Score: 0.75 - Positive)',
                    'News Analyst: Evaluating recent earnings report and market conditions',
                    'Risk Manager: Assessing portfolio risk and position sizing recommendations',
                    'Portfolio Manager: Final decision validation and trade approval',
                    'Analysis complete - Final recommendation generated'
                ],
                'result': '''Apple Inc. demonstrates strong investment potential based on comprehensive multi-agent analysis:

**Fundamental Analysis:**
- Revenue growth: 8.2% YoY, exceeding analyst expectations
- P/E ratio: 28.5 (reasonable for tech sector)
- Strong balance sheet with $165B cash reserves
- Market cap: $3.1T, maintaining leadership position

**Technical Analysis:**
- RSI: 45.2 (neutral, room for upside)
- MACD: Bullish crossover detected
- Support level: $175, Resistance: $195
- 20-day MA trending upward
- Volume indicators show institutional accumulation

**Sentiment Analysis:**
- Social media sentiment: 75% positive
- Analyst upgrades from 3 major firms this week
- Consumer confidence in Apple products remains high
- iPhone 15 launch driving positive momentum

**Risk Assessment:**
- Low volatility compared to tech peers
- Diversified product portfolio reduces risk
- Strong moat in ecosystem and brand loyalty
- Recommended position size: 5-8% of portfolio''',
                'agent_results': {
                    'fundamental_analyst': {
                        'revenue_growth': '8.2% YoY',
                        'pe_ratio': 28.5,
                        'cash_position': '$165B',
                        'debt_ratio': 'Low',
                        'recommendation': 'Strong Buy'
                    },
                    'technical_analyst': {
                        'rsi': 45.2,
                        'macd': 'Bullish crossover',
                        'support_level': '$175',
                        'resistance_level': '$195',
                        'trend': 'Upward',
                        'recommendation': 'Buy'
                    },
                    'sentiment_analyst': {
                        'social_sentiment': '75% positive',
                        'news_sentiment': '68% positive',
                        'analyst_ratings': '12 Buy, 3 Hold, 1 Sell',
                        'recommendation': 'Positive'
                    }
                },
                'technical_analysis': {
                    'RSI (14-day)': '45.2 - Neutral',
                    'MACD': 'Bullish crossover - Buy signal',
                    '20-day MA': '$182.50 - Uptrend',
                    '50-day MA': '$178.25 - Above price',
                    'Volume': 'Above average - Accumulation',
                    'Bollinger Bands': 'Price near middle band'
                },
                'fundamental_analysis': {
                    'Market Cap': '$3.1 Trillion',
                    'P/E Ratio': '28.5',
                    'Revenue Growth': '8.2% YoY',
                    'Profit Margin': '25.8%',
                    'ROE': '147.8%',
                    'Debt/Equity': '0.18 - Low',
                    'Cash Position': '$165 Billion'
                },
                'risk_assessment': '''Risk Level: LOW-MODERATE

Positive Risk Factors:
• Strong brand moat and customer loyalty
• Diversified product ecosystem
• Consistent cash generation
• Conservative debt levels

Risk Considerations:
• High valuation multiples
• Regulatory scrutiny potential
• China market dependency
• Technology disruption risks

Recommended position size: 5-8% of portfolio
Stop loss: $170 (-8% from entry)
Take profit targets: $200 (+15%), $220 (+25%)'''
            }
        elif analysis_id not in analysis_progress:
            return jsonify({
                'error': 'Analysis not found',
                'analysis_id': analysis_id
            }), 404
        else:
            data = analysis_progress[analysis_id]
        
        # Generate PDF
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from io import BytesIO
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor='darkblue',
            spaceAfter=30,
            alignment=1  # Center
        )
        
        # Build comprehensive PDF content
        story = []
        
        # Custom styles for better formatting
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor='darkblue',
            spaceAfter=12,
            spaceBefore=20
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            textColor='navy',
            spaceAfter=8,
            spaceBefore=12
        )
        
        # Title
        story.append(Paragraph("TradingAgents Multi-Agent Analysis Report", title_style))
        story.append(Spacer(1, 12))
        
        # Executive Summary Box
        from reportlab.lib.colors import lightgrey, darkblue
        from reportlab.platypus import Table, TableStyle
        
        decision_color = 'green' if data.get('decision', '').upper() == 'BUY' else 'red' if data.get('decision', '').upper() == 'SELL' else 'orange'
        
        exec_summary = [
            ['Analysis ID:', analysis_id],
            ['Symbol:', data.get('symbol', 'Unknown')],
            ['Company:', data.get('company_name', 'N/A')],
            ['Analysis Date:', data.get('date', 'Unknown')],
            ['Duration:', data.get('duration_formatted', 'Unknown')],
            ['Final Decision:', f"<font color='{decision_color}'><b>{data.get('decision', 'Unknown')}</b></font>"],
        ]
        
        exec_table = Table(exec_summary, colWidths=[2.5*inch, 3.5*inch])
        exec_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), lightgrey),
            ('TEXTCOLOR', (0,0), (-1,-1), 'black'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 1, 'black')
        ]))
        
        story.append(exec_table)
        story.append(Spacer(1, 20))
        
        # Analysis Progress Timeline
        story.append(Paragraph("Analysis Timeline:", heading_style))
        messages = data.get('messages', [])
        for i, message in enumerate(messages, 1):
            # Clean the message text
            clean_message = str(message).replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(f"<b>Step {i}:</b> {clean_message}", styles['Normal']))
            story.append(Spacer(1, 4))
        
        story.append(Spacer(1, 20))
        
        # Detailed Analysis Results
        if 'result' in data and data['result']:
            story.append(Paragraph("Comprehensive Analysis Results:", heading_style))
            
            # Parse and format the analysis result
            result = data['result']
            if isinstance(result, dict):
                # If result is structured data, format it nicely
                for section, content in result.items():
                    story.append(Paragraph(f"{section.replace('_', ' ').title()}:", subheading_style))
                    if isinstance(content, (list, dict)):
                        story.append(Paragraph(str(content), styles['Normal']))
                    else:
                        clean_content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(clean_content, styles['Normal']))
                    story.append(Spacer(1, 8))
            else:
                # Clean and format the result text
                clean_result = str(result).replace('<', '&lt;').replace('>', '&gt;')
                # Split into paragraphs for better readability
                paragraphs = clean_result.split('\n\n')
                for para in paragraphs:
                    if para.strip():
                        story.append(Paragraph(para.strip(), styles['Normal']))
                        story.append(Spacer(1, 8))
        
        # Agent Analysis Breakdown (if available)
        if 'agent_results' in data:
            story.append(Paragraph("Individual Agent Analysis:", heading_style))
            
            agent_results = data['agent_results']
            for agent_name, agent_data in agent_results.items():
                story.append(Paragraph(f"{agent_name.replace('_', ' ').title()}:", subheading_style))
                
                if isinstance(agent_data, dict):
                    for key, value in agent_data.items():
                        if value:
                            clean_value = str(value).replace('<', '&lt;').replace('>', '&gt;')
                            story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {clean_value}", styles['Normal']))
                else:
                    clean_data = str(agent_data).replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(clean_data, styles['Normal']))
                
                story.append(Spacer(1, 10))
        
        # Technical Indicators (if available)
        if 'technical_analysis' in data:
            story.append(Paragraph("Technical Analysis:", heading_style))
            tech_data = data['technical_analysis']
            
            if isinstance(tech_data, dict):
                for indicator, value in tech_data.items():
                    story.append(Paragraph(f"<b>{indicator}:</b> {value}", styles['Normal']))
                    story.append(Spacer(1, 4))
            else:
                clean_tech = str(tech_data).replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(clean_tech, styles['Normal']))
            
            story.append(Spacer(1, 15))
        
        # Fundamental Analysis (if available)
        if 'fundamental_analysis' in data:
            story.append(Paragraph("Fundamental Analysis:", heading_style))
            fund_data = data['fundamental_analysis']
            
            if isinstance(fund_data, dict):
                for metric, value in fund_data.items():
                    story.append(Paragraph(f"<b>{metric}:</b> {value}", styles['Normal']))
                    story.append(Spacer(1, 4))
            else:
                clean_fund = str(fund_data).replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(clean_fund, styles['Normal']))
            
            story.append(Spacer(1, 15))
        
        # Risk Assessment (if available)
        if 'risk_assessment' in data:
            story.append(Paragraph("Risk Assessment:", heading_style))
            risk_data = data['risk_assessment']
            clean_risk = str(risk_data).replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(clean_risk, styles['Normal']))
            story.append(Spacer(1, 15))
        
        # Final Recommendation Summary
        story.append(Paragraph("Final Recommendation:", heading_style))
        recommendation = f"""
        Based on the comprehensive multi-agent analysis involving fundamental analysts, 
        technical analysts, sentiment analysts, and risk managers, the final trading 
        decision for {data.get('symbol', 'the analyzed symbol')} is: 
        <font color='{decision_color}'><b>{data.get('decision', 'Unknown')}</b></font>
        
        This recommendation is based on {len(messages)} analysis steps completed over 
        {data.get('duration_formatted', 'unknown duration')}.
        """
        story.append(Paragraph(recommendation, styles['Normal']))
        
        # Disclaimer
        story.append(Spacer(1, 30))
        disclaimer = """
        <b>Disclaimer:</b> This analysis is generated by AI agents and is for informational 
        purposes only. It does not constitute financial advice. Please conduct your own 
        research and consult with financial professionals before making investment decisions.
        Trading involves risk and you may lose money.
        """
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=8,
            textColor='grey',
            alignment=1  # Center
        )
        story.append(Paragraph(disclaimer, disclaimer_style))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Return PDF file
        from flask import Response
        return Response(
            buffer.read(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename=analysis_{data.get("symbol", "unknown")}_{analysis_id}.pdf'}
        )
        
    except Exception as e:
        logger.error(f"❌ PDF Download error: {e}")
        return jsonify({
            'error': 'PDF download failed',
            'message': str(e)
        }), 500

@app.route('/api/stock-info/<symbol>')
def get_stock_info(symbol):
    """Get current stock information including price, P/E, market cap, etc."""
    try:
        import yfinance as yf
        
        # Get stock data
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1d")
        
        # Extract key metrics
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None and not hist.empty:
            current_price = float(hist['Close'].iloc[-1])
        
        # Format metrics
        stock_data = {
            'symbol': symbol,
            'current_price': round(current_price, 2) if current_price else None,
            'currency': info.get('currency', 'USD'),
            'market_cap': format_market_cap(info.get('marketCap')),
            'pe_ratio': round(info.get('trailingPE'), 2) if info.get('trailingPE') else None,
            'dividend_yield': round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else None,
            'day_change_pct': round(info.get('regularMarketChangePercent', 0), 2),
            'volume': format_volume(info.get('volume')),
            'avg_volume': format_volume(info.get('averageVolume')),
            'fifty_two_week_high': round(info.get('fiftyTwoWeekHigh'), 2) if info.get('fiftyTwoWeekHigh') else None,
            'fifty_two_week_low': round(info.get('fiftyTwoWeekLow'), 2) if info.get('fiftyTwoWeekLow') else None,
            'company_name': info.get('longName', symbol)
        }
        
        return jsonify(stock_data)
        
    except Exception as e:
        logger.error(f"Error fetching stock info for {symbol}: {e}")
        return jsonify({'error': str(e), 'symbol': symbol}), 500

def format_market_cap(market_cap):
    """Format market cap in readable format"""
    if not market_cap:
        return None
    
    if market_cap >= 1e12:
        return f"${market_cap/1e12:.1f}T"
    elif market_cap >= 1e9:
        return f"${market_cap/1e9:.1f}B"
    elif market_cap >= 1e6:
        return f"${market_cap/1e6:.1f}M"
    else:
        return f"${market_cap:,.0f}"

def format_volume(volume):
    """Format volume in readable format"""
    if not volume:
        return None
    
    if volume >= 1e9:
        return f"{volume/1e9:.1f}B"
    elif volume >= 1e6:
        return f"{volume/1e6:.1f}M"
    elif volume >= 1e3:
        return f"{volume/1e3:.1f}K"
    else:
        return f"{volume:,.0f}"

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
        'BA': 'Boeing Company',
        'JPM': 'JPMorgan Chase & Co.',
        'JNJ': 'Johnson & Johnson',
        'V': 'Visa Inc.',
        'WMT': 'Walmart Inc.',
        'PG': 'Procter & Gamble Co.',
        'HD': 'Home Depot Inc.',
        'MA': 'Mastercard Inc.',
        'DIS': 'Walt Disney Co.',
        'VZ': 'Verizon Communications Inc.',
        'PFE': 'Pfizer Inc.',
        'KO': 'Coca-Cola Co.',
        'PEP': 'PepsiCo Inc.',
        'T': 'AT&T Inc.',
        'XOM': 'Exxon Mobil Corp.',
        'CVX': 'Chevron Corp.',
        'ABT': 'Abbott Laboratories',
        'COST': 'Costco Wholesale Corp.',
        'AVGO': 'Broadcom Inc.',
        'SHOP': 'Shopify Inc.',
        'GEV': 'GE Vernova Inc.',
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
        'BA': 'Boeing Company',
        'JPM': 'JPMorgan Chase & Co.',
        'JNJ': 'Johnson & Johnson',
        'V': 'Visa Inc.',
        'WMT': 'Walmart Inc.',
        'PG': 'Procter & Gamble Co.',
        'HD': 'Home Depot Inc.',
        'MA': 'Mastercard Inc.',
        'DIS': 'Walt Disney Co.',
        'VZ': 'Verizon Communications Inc.',
        'PFE': 'Pfizer Inc.',
        'KO': 'Coca-Cola Co.',
        'PEP': 'PepsiCo Inc.',
        'T': 'AT&T Inc.',
        'XOM': 'Exxon Mobil Corp.',
        'CVX': 'Chevron Corp.',
        'ABT': 'Abbott Laboratories',
        'COST': 'Costco Wholesale Corp.',
        'AVGO': 'Broadcom Inc.',
        'SHOP': 'Shopify Inc.',
        'GEV': 'GE Vernova Inc.',
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
    
    matches = []
    query_upper = query.upper()
    
    # Search in hardcoded list first
    for symbol, company_name in company_names.items():
        if symbol.startswith(query_upper) or query_upper in company_name.upper():
            matches.append({
                'symbol': symbol,
                'company_name': company_name
            })
    
    # If no matches found and online tools enabled, try FINNHUB API
    if not matches and os.getenv("ONLINE_TOOLS", "true").lower() == "true":
        try:
            import finnhub
            finnhub_api_key = os.getenv("FINNHUB_API_KEY")
            
            if finnhub_api_key and finnhub_api_key != "your_finnhub_api_key_here":
                finnhub_client = finnhub.Client(api_key=finnhub_api_key)
                
                # Search for companies using FINNHUB
                search_results = finnhub_client.symbol_lookup(query_upper)
                
                if search_results and 'result' in search_results:
                    for result in search_results['result'][:10]:
                        if result.get('symbol') and result.get('description'):
                            matches.append({
                                'symbol': result['symbol'],
                                'company_name': result['description']
                            })
            else:
                # Fallback: check if query looks like a stock symbol and allow it
                if len(query_upper) <= 6 and query_upper.isalpha():
                    matches.append({
                        'symbol': query_upper,
                        'company_name': f'{query_upper} (Symbol lookup - configure FINNHUB API for company name)'
                    })
                        
        except Exception as e:
            logger.error(f"FINNHUB API search failed: {e}")
            # Fallback: allow symbol if it looks valid
            if len(query_upper) <= 6 and query_upper.isalpha():
                matches.append({
                    'symbol': query_upper,
                    'company_name': f'{query_upper} (Lookup failed - check FINNHUB API key)'
                })
    
    # Sort by symbol length (exact matches first)
    matches.sort(key=lambda x: (len(x['symbol']), x['symbol']))
    
    return jsonify({
        'query': query,
        'matches': matches[:10],  # Limit to 10 results
        'source': 'hardcoded+finnhub' if matches else 'none'
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