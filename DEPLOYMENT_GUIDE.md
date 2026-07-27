# Zero Orchestrator Production Deployment Guide

## Deployment Configuration Complete

### Backend (Render) Configuration
- **Service Name**: zero-orchestrator-api
- **Expected URL**: https://zero-orchestrator-api.onrender.com
- **Database**: Supabase PostgreSQL
- **Framework**: FastAPI + FastMCP

### Frontend (Vercel) Configuration
- **Project Name**: zero-orchestrator
- **Expected URL**: https://zero-orchestrator.vercel.app
- **Framework**: Vite + React

## Environment Variables Configured

### Backend Environment Variables
- `DATABASE_URL`: postgresql://postgres.xvvpmofnuvptnbhkvazg:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
- `SUPABASE_URL`: https://xvvpmofnuvptnbhkvazg.supabase.co
- `SUPABASE_SERVICE_ROLE_KEY`: sb_publishable_HK5uxbM2U7q13aK9NGQYHA_36qnmqAM
- `SECRET_KEY`: zero-terminal-production-secret-key-2024
- `ALLOWED_ORIGINS`: https://zero-orchestrator.vercel.app
- `PYTHON_VERSION`: 3.13

### Frontend Environment Variables
- `VITE_API_URL`: https://zero-orchestrator-api.onrender.com

## Manual Deployment Steps

### Backend Deployment to Render

1. **Prepare Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/zero-orchestrator.git
   git push -u origin main
   ```

2. **Deploy to Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: zero-orchestrator-api
     - **Root Directory**: backend
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables (see above)
   - Click "Deploy Web Service"

3. **Verify Deployment**
   - Wait for deployment to complete
   - Check health: `https://zero-orchestrator-api.onrender.com/health`
   - Expected response: `{"status":"ok"}`

### Frontend Deployment to Vercel

1. **Deploy to Vercel**
   - Go to https://vercel.com/dashboard
   - Click "Add New Project"
   - Import your GitHub repository
   - Configure:
     - **Root Directory**: frontend
     - **Framework Preset**: Vite
     - **Build Command**: `npm run build`
     - **Output Directory**: dist
   - Add environment variable:
     - `VITE_API_URL`: `https://zero-orchestrator-api.onrender.com`
   - Click "Deploy"

2. **Verify Deployment**
   - Wait for deployment to complete
   - Visit: `https://zero-orchestrator.vercel.app`
   - Test login/registration functionality

## Final Deployment URLs

### Backend Endpoints
- **Health Check**: https://zero-orchestrator-api.onrender.com/health
- **API Documentation**: https://zero-orchestrator-api.onrender.com/docs
- **FastMCP Endpoint**: https://zero-orchestrator-api.onrender.com/mcp
- **User Registration**: https://zero-orchestrator-api.onrender.com/api/auth/register
- **User Login**: https://zero-orchestrator-api.onrender.com/api/auth/login
- **MCP Token Generation**: https://zero-orchestrator-api.onrender.com/api/mcp/token

### Frontend Endpoints
- **Web Application**: https://zero-orchestrator.vercel.app
- **Developer Settings**: https://zero-orchestrator.vercel.app (after login)

## Post-Deployment Verification

### Backend Health Checks
- [ ] Health endpoint responds: `GET /health`
- [ ] API docs accessible: `GET /docs`
- [ ] MCP endpoint accessible: `GET /mcp`
- [ ] Database connection established
- [ ] User registration works: `POST /api/auth/register`
- [ ] User login works: `POST /api/auth/login`
- [ ] MCP token generation works: `POST /api/mcp/token`

### Frontend Functionality
- [ ] Frontend loads without errors
- [ ] Login modal opens correctly
- [ ] Registration works end-to-end
- [ ] Developer Settings panel accessible
- [ ] MCP token generation works
- [ ] API calls to backend succeed

### Security Verification
- [ ] HTTPS enabled on both frontend and backend
- [ ] CORS properly configured
- [ ] Environment variables not exposed
- [ ] Database credentials secure
- [ ] JWT secret key is strong

## Troubleshooting

### Common Issues

**Backend won't start**
- Check Render logs for database connection errors
- Verify `DATABASE_URL` format is correct
- Ensure all dependencies are in `requirements.txt`

**Frontend can't connect to backend**
- Verify `VITE_API_URL` is set correctly
- Check CORS configuration on backend
- Ensure backend is deployed and accessible

**Database errors**
- Verify Supabase database is running
- Check database connection string format
- Ensure database migrations ran successfully

## Production Considerations

### Database
- Supabase PostgreSQL with connection pooling
- Automatic backups provided by Supabase
- Monitor database connection limits

### Security
- JWT token authentication
- MCP token validation
- CORS protection
- Environment variable isolation

### Performance
- FastAPI async endpoints
- SQLModel with SQLAlchemy
- Database query optimization
- CDN for static assets (Vercel)

## Credentials Summary

### Supabase
- **Database URL**: postgresql://postgres.xvvpmofnuvptnbhkvazg:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
- **Project URL**: https://xvvpmofnuvptnbhkvazg.supabase.co
- **Service Role Key**: sb_publishable_HK5uxbM2U7q13aK9NGQYHA_36qnmqAM

### Render
- **API Key**: rnd_bo83rX7s8bPZB3zcWEN3ZM6sN67z
- **Service Name**: zero-orchestrator-api

### Vercel
- **API Key**: vcp_10RI1Kr56LwPRzFRxmBZpm2rPXBi3bPOsTWTkq1yYzo89tpFfV1cBcfe
- **Project Name**: zero-orchestrator

## Next Steps

1. Push code to GitHub repository
2. Deploy backend to Render using the configuration above
3. Deploy frontend to Vercel using the configuration above
4. Update CORS origins with actual Vercel URL
5. Test all endpoints and functionality
6. Monitor deployment logs for any issues
