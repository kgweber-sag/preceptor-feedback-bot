# Preceptor Feedback Bot - Migration TODO List

**Migration Target**: Streamlit → FastAPI + HTMX + Google OAuth + Cloud Firestore

**Status**: Planning Complete - Ready for Implementation
**Timeline**: 6 weeks (estimated)
**Last Updated**: 2025-12-18

---

## Phase 1: Foundation & Authentication (Week 1)

### Setup & Infrastructure
- [ ] Create new directory structure (`app/`, `app/api/`, `app/services/`, etc.)
- [ ] Initialize new Git branch: `fastapi-migration`
- [ ] Create `app/main.py` with basic FastAPI app
- [ ] Set up `app/config.py` with enhanced configuration
- [ ] Create `requirements.txt` with new dependencies
- [ ] Create new `Dockerfile` for FastAPI/Uvicorn

### Google OAuth Setup
- [ ] Create OAuth 2.0 credentials in Google Cloud Console
  - Set redirect URI: `https://your-app.run.app/auth/callback`
  - Enable Google+ API
- [ ] Store secrets in Google Secret Manager
  - `oauth-client-id`
  - `oauth-client-secret`
  - `jwt-secret-key` (generate with `openssl rand -hex 32`)
- [ ] Implement `app/services/auth_service.py`
  - PKCE code_verifier/code_challenge generation
  - OAuth redirect URL builder
  - Token exchange logic
  - JWT generation/validation
  - Domain restriction logic
- [ ] Create `app/api/auth.py` routes
  - `GET /auth/login`
  - `GET /auth/callback`
  - `POST /auth/logout`
  - `GET /auth/verify`
- [ ] Implement `app/middleware/auth_middleware.py`
  - JWT validation from cookies
  - Inject current_user into request state

### Database Setup
- [ ] Enable Firestore in GCP project
- [ ] Create Firestore security rules file
- [ ] Deploy security rules to Firestore
- [ ] Implement `app/services/firestore_service.py`
  - Connection initialization
  - Helper methods for CRUD operations
- [ ] Create Pydantic models in `app/models/`
  - `user.py` (User, UserCreate, UserInDB)
  - `conversation.py` (Conversation, Message)
  - `feedback.py` (Feedback, FeedbackVersion)

### Templates & UI Foundation
- [ ] Create `app/templates/base.html`
  - HTML structure with Tailwind CSS CDN
  - HTMX script tag
  - Navigation placeholder
  - Global error/success message containers
- [ ] Create `app/templates/login.html`
  - "Sign in with Google" button
  - Institutional branding
- [ ] Create `app/static/css/styles.css` (custom styles)

### Deployment Test
- [ ] Update `cloudbuild.yaml`
  - Change to `--no-allow-unauthenticated`
  - Add `--set-secrets` for OAuth and JWT
- [ ] Deploy to Cloud Run
- [ ] Test OAuth login flow end-to-end
- [ ] Verify JWT cookie is set correctly
- [ ] Test domain restriction (if enabled)

---

## Phase 2: Core Conversation Logic (Week 2)

### VertexAIClient Migration
- [ ] Copy `utils/vertex_ai_client.py` to `app/services/vertex_ai_client.py`
- [ ] Update import paths (config, logger)
- [ ] Add `conversation_id` parameter to `__init__`
- [ ] Modify `send_message()` to return dict instead of tuple
- [ ] Remove `save_conversation_log()` method (Firestore handles this)
- [ ] Test VertexAIClient in isolation (unit tests)

### Conversation Service
- [ ] Create `app/services/conversation_service.py`
  - `create_conversation(user_id, student_name)` - Initialize in Firestore
  - `send_message(conversation_id, user_message)` - Process message, update Firestore
  - `get_conversation(conversation_id)` - Retrieve from Firestore
  - `list_conversations(user_id, filters)` - Query user's conversations
  - `archive_conversation(conversation_id)` - Mark as completed

### Conversation API Endpoints
- [ ] Implement `app/api/conversations.py`
  - `POST /conversations` - Create new conversation
  - `GET /conversations/{id}` - Get conversation page
  - `POST /conversations/{id}/messages` - Send message (HTMX)
  - `GET /conversations/{id}/messages` - Get all messages (HTMX)
- [ ] Add authentication dependency to all routes
- [ ] Add Firestore ownership checks (user can only access own conversations)

### Conversation UI Templates
- [ ] Create `app/templates/conversation.html`
  - Student name display
  - Message list container (`#message-list`)
  - Chat input form (HTMX post to `/messages`)
  - Progress indicator (turn count)
  - "Generate Feedback" button
- [ ] Create `app/templates/components/message.html`
  - User message bubble (right-aligned, blue)
  - Assistant message bubble (left-aligned, gray)
  - Timestamp display
  - Loading spinner for pending messages

### Testing
- [ ] Test conversation creation via UI
- [ ] Test message sending and receiving
- [ ] Test HTMX message appending
- [ ] Verify Firestore updates correctly
- [ ] Test premature feedback detection
- [ ] Test conversation turn limit (MAX_TURNS)

---

## Phase 3: Feedback Generation & Refinement (Week 3)

### Feedback Service
- [ ] Create `app/services/feedback_service.py`
  - `generate_feedback(conversation_id)` - Call VertexAI, create Firestore doc
  - `refine_feedback(feedback_id, refinement_request)` - Add version
  - `get_feedback(conversation_id)` - Retrieve from Firestore
  - `download_feedback(feedback_id)` - Generate .txt file

### Feedback API Endpoints
- [ ] Implement `app/api/feedback.py`
  - `POST /conversations/{id}/feedback/generate` - Generate feedback (HTMX)
  - `POST /conversations/{id}/feedback/refine` - Refine feedback (HTMX)
  - `GET /conversations/{id}/feedback` - View feedback page
  - `GET /conversations/{id}/feedback/download` - Download .txt file
  - `POST /conversations/{id}/finish` - Archive conversation, redirect

### Feedback UI Templates
- [ ] Create `app/templates/feedback.html`
  - Feedback content display (`#feedback-content`)
  - Refinement form (HTMX post to `/refine`)
  - Download button
  - "Finish & Save" button
- [ ] Create `app/templates/components/feedback_content.html`
  - Formatted feedback with markdown rendering
  - Version indicator

### Testing
- [ ] Test feedback generation from completed conversation
- [ ] Test feedback refinement (multiple iterations)
- [ ] Test download functionality (.txt format correct)
- [ ] Test "Finish & Save" archives conversation
- [ ] Verify feedback versioning in Firestore

---

## Phase 4: Dashboard & Conversation History (Week 4)

### Dashboard Service
- [ ] Enhance `conversation_service.py`
  - `search_conversations(user_id, query, filters, pagination)` - Full-text search
  - Add Firestore composite indexes for common queries

### Dashboard API Endpoints
- [ ] Create `app/api/user.py`
  - `GET /dashboard` - Dashboard page (with pagination)
  - `GET /api/conversations` - JSON API for search/filter

### Dashboard UI Templates
- [ ] Create `app/templates/dashboard.html`
  - Search/filter bar
  - Conversation list container (`#conversation-list`)
  - Infinite scroll trigger (HTMX)
  - "New Conversation" button
  - Empty state (no conversations yet)
- [ ] Create `app/templates/components/conversation_card.html`
  - Student name
  - Last message preview (truncated)
  - Turn count, timestamp
  - Status badge (active/completed/archived)
  - Click to open conversation

### Search & Filtering
- [ ] Implement search by student name (case-insensitive)
- [ ] Filter by status (active/completed/archived)
- [ ] Filter by date range (created_at, updated_at)
- [ ] Sort by most recent, oldest, student name

### Pagination
- [ ] Implement infinite scroll with HTMX
- [ ] Load 20 conversations per page
- [ ] Show loading spinner on scroll trigger

### Testing
- [ ] Test dashboard loads conversations
- [ ] Test search functionality
- [ ] Test filtering by status and date
- [ ] Test pagination (scroll to load more)
- [ ] Test "New Conversation" button navigates correctly

---

## Phase 5: Mobile UI & Polish (Week 5)

### Responsive Design
- [ ] Implement Tailwind responsive breakpoints in all templates
  - Mobile (< 768px): Single column, sticky input
  - Tablet (768-1024px): Two columns
  - Desktop (> 1024px): Three columns option
- [ ] Add mobile navigation
  - Hamburger menu for mobile
  - Persistent sidebar for desktop
- [ ] Optimize chat input for mobile
  - Sticky bottom positioning
  - Auto-focus on page load (desktop only)
  - Mobile keyboard hints (type="text", autocomplete)

### Touch Optimization
- [ ] Increase button min-height to 48px for touch targets
- [ ] Add touch-friendly spacing (padding, margins)
- [ ] Test tap interactions on iOS and Android
- [ ] Ensure no horizontal scrolling on mobile

### Loading States & Indicators
- [ ] Add HTMX loading spinners
  - Message sending
  - Feedback generation
  - Page navigation
- [ ] Add skeleton loaders for dashboard cards
- [ ] Implement optimistic UI updates (show user message immediately)

### Error Handling UX
- [ ] Create global error toast component
- [ ] Handle HTMX errors gracefully (display user-friendly messages)
- [ ] Add retry buttons for failed requests
- [ ] Handle offline mode (show "No connection" message)

### Accessibility
- [ ] Add ARIA labels to buttons and form inputs
- [ ] Ensure keyboard navigation works (tab order)
- [ ] Test with screen reader (NVDA/VoiceOver)
- [ ] Ensure color contrast meets WCAG AA standards
- [ ] Add focus indicators for keyboard users

### Testing
- [ ] Test on mobile browsers (Safari iOS, Chrome Android)
- [ ] Test on tablets (iPad, Android tablets)
- [ ] Test desktop browsers (Chrome, Firefox, Safari, Edge)
- [ ] Test different screen sizes with browser dev tools
- [ ] Test accessibility with Lighthouse audit

---

## Phase 6: Testing, Documentation & Deployment (Week 6)

### Integration Testing
- [ ] Write integration tests for OAuth flow
- [ ] Write tests for conversation creation and messaging
- [ ] Write tests for feedback generation and refinement
- [ ] Write tests for dashboard search and filtering
- [ ] Write tests for authorization (users can't access others' data)

### Load Testing
- [ ] Set up load testing with Locust or k6
- [ ] Test 10+ concurrent conversations
- [ ] Measure response times (target: < 2s for messages)
- [ ] Test Firestore query performance
- [ ] Test rate limit handling (Vertex AI 429 errors)

### Security Audit
- [ ] Review Firestore security rules (users can only access own data)
- [ ] Test JWT expiration and refresh
- [ ] Test CSRF protection (SameSite cookies)
- [ ] Test XSS prevention (Jinja2 autoescaping)
- [ ] Test OAuth flow security (PKCE, state parameter)
- [ ] Review secrets management (no hardcoded secrets)
- [ ] Test domain restriction enforcement

### Documentation
- [ ] Update README.md
  - New architecture overview
  - Setup instructions
  - OAuth configuration
  - Firestore setup
  - Environment variables
- [ ] Update CLAUDE.md with new architecture patterns
- [ ] Create API documentation (FastAPI auto-docs at `/docs`)
- [ ] Document Firestore data models
- [ ] Create user guide (how to use the app)

### Production Deployment
- [ ] Review environment variables in Cloud Run
- [ ] Verify Secret Manager integration
- [ ] Set min/max instances (0-10)
- [ ] Set appropriate timeout (600s)
- [ ] Deploy to production
- [ ] Verify OAuth works in production
- [ ] Test end-to-end in production environment
- [ ] Monitor logs for errors

### Monitoring & Observability
- [ ] Set up Cloud Logging alerts for errors
- [ ] Monitor Firestore usage and costs
- [ ] Monitor Vertex AI API usage and rate limits
- [ ] Set up uptime monitoring (Cloud Monitoring)

---

## Phase 7: Optional Enhancements (Future Work)

### Survey Feature (from original app)
- [ ] Create survey template
- [ ] Add survey endpoints
- [ ] Store survey responses in Firestore
- [ ] Show survey after "Finish & Save"

### Advanced Features
- [ ] Bulk export of feedback (CSV/Excel)
- [ ] Student performance trends (multiple encounters)
- [ ] Preceptor analytics dashboard
- [ ] Email notifications (feedback ready)
- [ ] Collaboration (multiple preceptors for same student)

### Performance Optimizations
- [ ] Implement Redis caching for frequently accessed conversations
- [ ] Use Firestore offline persistence
- [ ] Optimize bundle size (tree-shake Tailwind CSS)
- [ ] Implement service worker for PWA

---

## Migration Checklist (Pre-Cutover)

Before switching from Streamlit to FastAPI in production:

- [ ] All Phase 1-6 tasks completed
- [ ] Integration tests passing
- [ ] Load tests passing
- [ ] Security audit completed with no critical issues
- [ ] Documentation updated
- [ ] OAuth configured for production domain
- [ ] Firestore security rules deployed
- [ ] Cloud Run deployed successfully
- [ ] End-to-end testing in production complete
- [ ] Stakeholder approval obtained
- [ ] Rollback plan documented

---

## Notes & Decisions

**Date**: 2025-12-18
**Decisions Made**:
- Complete rewrite (not incremental)
- Cloud Firestore for database
- Hybrid OAuth domain restriction (configurable)
- No migration of existing logs (fresh start)

**Critical Files from Old Codebase**:
- `prompts/system_prompt.md` - Keep unchanged
- `utils/vertex_ai_client.py` - Migrate to `app/services/`
- `config.py` - Reference for enhancement
- `app.py` - Reference for workflow replication

**Risks**:
- OAuth configuration complexity
- Mobile UI testing time
- Firestore query performance at scale
- Vertex AI rate limits in production

**Mitigation**:
- OAuth: Test thoroughly in staging environment
- Mobile: Use real devices for testing
- Firestore: Monitor queries, add indexes as needed
- Rate limits: Preserve exponential backoff logic

---

## Contact & Support

For questions or issues during migration:
- Review this TODO list
- Check MIGRATION_PLAN.md in `.claude/plans/`
- Consult existing CLAUDE.md for current architecture
- Test incrementally, deploy often
