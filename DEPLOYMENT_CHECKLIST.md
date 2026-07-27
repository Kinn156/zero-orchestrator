# Zero Orchestrator Production Deployment Checklist

## Backend Deployment (Render)

### Prerequisites
- [ ] Render account created
- [ ] PostgreSQL database provisioned on Render
- [ ] GitHub repository with backend code

### Environment Variables
Set these in your Render dashboard:
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:password@host:port/database`)
- `SECRET_KEY`: Strong random string for JWT signing (generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `ALLOWED_ORIGINS`: Comma-separated list of frontend URLs (e.g., `https://your-frontend.vercel.app`)
- `PYTHON_VERSION`: `3.13`

### Deployment Steps
1. **Connect Repository**
   - Link your GitHub repository to Render
   - Select `backend/` as the root directory

2. **Configure Service**
   - Service type: Web Service
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Database Setup**
   - Create PostgreSQL database on Render
   - Copy connection string to `DATABASE_URL` environment variable

4. **Deploy**
   - Click "Deploy" to start the deployment
   - Monitor deployment logs for any errors

5. **Verify Deployment**
   - Check health endpoint: `https://your-backend.onrender.com/health`
   - Expected response: `{"status":"ok"}`

## Frontend Deployment (Vercel)

### Prerequisites
- [ ] Vercel account created
- [ ] GitHub repository with frontend code

### Environment Variables
Set these in Vercel project settings:
- `VITE_API_URL`: Backend API URL (e.g., `https://your-backend.onrender.com`)

### Deployment Steps
1. **Connect Repository**
   - Link your GitHub repository to Vercel
   - Select `frontend/` as the root directory

2. **Configure Project**
   - Framework preset: Vite
   - Build command: `npm run build`
   - Output directory: `dist`

3. **Environment Variables**
   - Add `VITE_API_URL` with your backend URL

4. **Deploy**
   - Click "Deploy" to start the deployment
   - Monitor deployment logs for any errors

5. **Verify Deployment**
   - Visit your Vercel URL
   - Check that the frontend loads correctly
   - Test login/registration functionality

## Post-Deployment Verification

### Backend Health Checks
- [ ] Health endpoint responds: `GET /health`
- [ ] CORS headers allow frontend origin
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
- Verify PostgreSQL database is running
- Check database connection string format
- Ensure database migrations ran successfully

**Authentication failures**
- Verify `SECRET_KEY` is set and consistent
- Check JWT token expiration settings
- Ensure user passwords are hashed correctly

## Production Considerations

### Database
- Consider adding database backups
- Monitor database connection limits
- Plan for database scaling if needed

### Security
- Rotate `SECRET_KEY` periodically
- Implement rate limiting on API endpoints
- Add request logging and monitoring
- Consider adding API key management

### Performance
- Monitor API response times
- Consider adding caching for frequently accessed data
- Implement database query optimization
- Set up CDN for static assets

### Monitoring
- Set up error tracking (e.g., Sentry)
- Monitor application performance
- Set up uptime monitoring
- Configure alerting for critical failures

## Rollback Plan

If deployment fails:
1. Revert to previous git commit
2. Redeploy using Render/Vercel rollback feature
3. Verify health endpoints
4. Test critical functionality
5. Communicate with users if needed

## Contact Information

- Backend URL: [Fill in after deployment]
- Frontend URL: [Fill in after deployment]
- Database: Render PostgreSQL
- Support: [Your contact information]
