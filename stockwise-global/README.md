# StockWise - AI-Powered Stock Analysis Platform (Global Version)

## Overview

StockWise is an AI-powered stock analysis platform designed for global users. It provides real-time stock data, AI-driven insights, and portfolio management tools.

## Features

- **Real-time Stock Data**: Live prices from Yahoo Finance API
- **AI Analysis**: Intelligent stock analysis and recommendations
- **Watchlist**: Track your favorite stocks
- **Market Coverage**: US Stocks, China A-Shares, Hong Kong
- **Multi-language Support**: English (Global), Chinese (Simplified)
- **Payment Integration**: PayPal, Credit Cards, Alipay

## Pricing Plans

| Plan | Monthly | Yearly | Features |
|------|---------|--------|----------|
| Free | $0 | $0 | Basic search, 5 watchlist stocks |
| Pro | $19.99 | $199.99 | Unlimited watchlist, 50 AI analyses/month |
| Enterprise | $49.99 | $499.99 | Unlimited AI, API access, custom reports |

## Tech Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Backend**: Node.js, Express
- **API**: Yahoo Finance API
- **Payment**: PayPal SDK, Alipay
- **Deployment**: Railway/Render

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/stockwise-global.git

# Install dependencies
npm install

# Start the server
npm start
```

## Environment Variables

Create a `.env` file:

```env
PORT=3000
NODE_ENV=production
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
```

## API Endpoints

- `GET /api/stocks` - Get all tracked stocks
- `GET /api/stocks/:symbol` - Get specific stock data
- `GET /api/health` - Health check

## Deployment

### Railway

1. Push code to GitHub
2. Connect Railway to GitHub repo
3. Set environment variables
4. Deploy

### Render

1. Create new Web Service
2. Connect GitHub repo
3. Set build command: `npm install`
4. Set start command: `npm start`
5. Deploy

## Stock Data Refresh

The application automatically refreshes stock data:
- **Frequency**: Every 5 minutes during market hours
- **Market Hours**: Mon-Fri, 9:30 AM - 4:00 PM EST
- **API Source**: Yahoo Finance

## Payment Setup

### PayPal

1. Create PayPal Developer account
2. Create app to get Client ID
3. Create subscription plans in PayPal Dashboard
4. Update `api/paypal-integration.js` with your credentials

### Alipay

1. Register for Alipay merchant account
2. Get merchant ID and API keys
3. Configure in payment settings

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License - see LICENSE file for details

## Support

- Email: support@stockwise.com
- Help Center: https://stockwise.com/help
- Feedback: https://stockwise.com/feedback

## Roadmap

- [ ] Mobile app (iOS/Android)
- [ ] Advanced charting tools
- [ ] Social trading features
- [ ] More market coverage (Europe, Japan)
- [ ] AI-powered portfolio optimization
