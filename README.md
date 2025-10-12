# 🤖 GemKey AI - The Gemini-Powered SEO Keyword Agent

GemKey AI is a comprehensive keyword research and SEO analysis platform powered by AI.

## ✨ Features

### 🔍 Core Keyword Research
- **AI-Powered Discovery**: Advanced keyword discovery using Google Gemini AI
- **Competitor Analysis**: Gap analysis between competitors
- **Search Intent Classification**: Classify keywords by search intent
- **Topic Clustering**: Semantic grouping of related keywords
- **Trend Forecasting**: Predict keyword trends with seasonal analysis
- **SERP Analysis**: Analyze search engine results pages


### 📊 Advanced Analytics
- **Real-time Metrics**: Volume, competition, CPC, and trend data
- **Performance Scoring**: AI-powered keyword scoring system
- **Database Storage**: MySQL database for persistent storage
- **Export Options**: CSV export with comprehensive data
- **Interactive Charts**: Plotly-powered visualizations

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd gemkey-ai

# Install dependencies
pip install -r requirements.txt

# Start Streamlit app
streamlit run app.py
```

## 📋 Prerequisites

- **Python 3.8+**
- **API Keys** (optional but recommended):
  - Google Gemini API key
  - SerpAPI key

## 🔧 Configuration

### Environment Variables
Create a `.env` file with your API keys:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key
SERPAPI_KEY=your_serpapi_key
```

## 🎯 Usage

### 1. Basic Keyword Research
1. Open http://localhost:8501
2. Enter your seed keyword
3. Choose analysis type (Quick or Comprehensive)
4. View results with metrics and recommendations

### 2. Advanced Features
- **Competitor Gap Analysis**: Compare keyword gaps between competitors
- **Topic Clustering**: Group related keywords semantically
- **Trend Forecasting**: Predict keyword performance
- **SERP Analysis**: Analyze search results opportunities

## 📁 Project Structure

```
gemkey-ai/
├── app.py                          # Main Streamlit application
├── src/                            # Source code modules
│   ├── agent.py                    # Main keyword discovery agent
│   ├── lightweight_agent.py        # Quick analysis agent
│   ├── competitor_gap_analyzer.py  # Competitor analysis
│   ├── topic_clusterer.py         # Topic clustering
│   ├── trend_forecaster.py        # Trend forecasting
│   └── ...                        # Other modules
├── cache/                         # Cached results
├── requirements.txt               # Python dependencies
└── README.md                      # Documentation
```

## 🔍 Monitoring & Logs

### View Logs
```bash
# Streamlit logs
streamlit run app.py --logger.level debug
```

## 🛠️ Development

### Extending Functionality
1. Add new modules to `src/`
2. Update `app.py` with new features
3. Add new analysis types and visualizations

### Testing
```bash
# Test individual modules
python -c "from src.agent import run_agent; print('Agent imported successfully')"
```

## 🚨 Troubleshooting

### Common Issues

1. **API key errors**
   - Verify API keys in `.env` file
   - Check API quotas and limits
   - Test API endpoints manually

2. **Streamlit not loading**
   ```bash
   streamlit run app.py --server.port 8502
   ```

3. **Module import errors**
   ```bash
   pip install -r requirements.txt
   ```

## 📈 Performance Optimization

### Caching
- Streamlit caching for expensive operations
- API response caching
- Database query optimization

### Resource Management
- API rate limiting
- Batch processing for large datasets

## 🔐 Security

### Production Deployment
- Change default passwords
- Use environment variables for secrets
- Enable HTTPS
- Configure firewall rules
- Regular security updates

### API Security
- Rate limiting
- API key authentication
- Input validation
- Error handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.




