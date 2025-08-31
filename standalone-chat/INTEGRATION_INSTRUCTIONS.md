# Rubben Chat Integration Instructions

## Overview
This is a standalone React component that provides a complete chat interface with document management and conversation history. The component is self-contained and can be easily integrated into any React project.

## Prerequisites

### Required Dependencies
Install these packages in your target project:

```bash
npm install lucide-react framer-motion
# or
yarn add lucide-react framer-motion
```

### Required Styles
Ensure your project has Tailwind CSS configured. If not, install it:

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Add Tailwind directives to your main CSS file:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

## Integration Steps

### 1. Copy the Component
Copy the `RubbenChat.tsx` file to your project's components directory.

### 2. Update Backend Configuration
Open `RubbenChat.tsx` and locate the `API_CONFIG` object at the top of the file:

```typescript
const API_CONFIG = {
  BASE_URL: "https://rubben-backend-production-5dff.up.railway.app", // <-- UPDATE THIS
  ENDPOINTS: {
    SEARCH: "/api/search",
    SESSIONS: "/api/conversation/sessions",
    SESSION_MESSAGES: (id: string) => `/api/conversation/sessions/${id}/messages`,
    DELETE_SESSION: (id: string) => `/api/conversation/sessions/${id}`,
    DOCUMENTS: "/api/documents",
    DELETE_DOCUMENT: (id: string) => `/api/documents/${id}`,
    INGEST: "/api/ingest/contextual/batch"
  }
};
```

Replace `BASE_URL` with your backend server URL. Keep the endpoints the same unless your backend uses different paths.

### 3. Import and Use the Component

```tsx
import RubbenChat from './components/RubbenChat';

function App() {
  return (
    <div className="h-screen">
      <RubbenChat />
    </div>
  );
}
```

**Important:** The component uses `absolute inset-0` positioning, so ensure its parent container has a defined height and `position: relative`.

### 4. Backend API Requirements

Your backend must implement the following endpoints:

#### Search Endpoint
- **POST** `/api/search`
- Request Body:
  ```json
  {
    "query": "string",
    "mode": "hybrid",
    "stream": true,
    "session_id": "string | null"
  }
  ```
- Response: Server-Sent Events (SSE) stream with phases:
  - `routing`, `search`, `synthesis`, `answer`, `complete`
  - `session_created` or `session_continued` with `session_id`
  - `query_enhanced` with enhanced query text

#### Sessions Endpoints
- **GET** `/api/conversation/sessions?limit=20&active_only=false`
  - Returns: `{ sessions: Session[] }`
  
- **GET** `/api/conversation/sessions/{id}/messages`
  - Returns: Array of session messages
  
- **DELETE** `/api/conversation/sessions/{id}`
  - Deletes a session

#### Documents Endpoints
- **GET** `/api/documents`
  - Returns: `{ success: boolean, documents: DocumentInfo[], total: number }`
  
- **DELETE** `/api/documents/{id}`
  - Deletes a document
  
- **POST** `/api/ingest/contextual/batch`
  - Content-Type: `multipart/form-data`
  - Fields: `files[]` (multiple files), `user_instructions` (optional)
  - Response: SSE stream with ingestion progress

## Customization Options

### 1. Change the Logo
Replace the `RubbenLogoSVG` component in the file with your own logo SVG:

```tsx
const RubbenLogoSVG = () => (
  <svg width="16" height="16" viewBox="0 0 24 24">
    {/* Your logo SVG content */}
  </svg>
);
```

### 2. Modify Placeholder Text
Update the `PLACEHOLDERS` array to customize the rotating placeholder messages:

```typescript
const PLACEHOLDERS = [
  "Your custom placeholder 1",
  "Your custom placeholder 2",
  "Your custom placeholder 3",
];
```

### 3. Adjust Sources
Modify the Sources section in the component to reflect your data sources:

```tsx
{/* Sources Section */}
<div className="space-y-3">
  <div className="flex items-center justify-between">
    <span className="text-sm font-medium text-gray-700">Your Source 1</span>
    <PulsingDot />
  </div>
  <div className="flex items-center justify-between">
    <span className="text-sm font-medium text-gray-700">Your Source 2</span>
    <PulsingDot />
  </div>
</div>
```

### 4. Styling Adjustments
The component uses Tailwind CSS classes. You can modify colors, spacing, and other styles directly in the component.

Key color classes to customize:
- `bg-black` / `hover:bg-gray-800` - Primary button colors
- `bg-blue-600/10` - Active state for Think/Deep Search buttons
- `bg-green-500` - Active/online indicators
- `border-gray-200` - Border colors

## Testing the Integration

1. **Test Basic Chat:**
   - Type a message and press Enter or click Send
   - Verify the message appears and gets a response

2. **Test Document Upload:**
   - Click the paperclip icon
   - Select one or more documents
   - Verify upload progress and completion

3. **Test Session Management:**
   - Start multiple conversations
   - Click on past conversations in the right sidebar
   - Verify sessions load correctly

4. **Test Document Management:**
   - Click the Documents dropdown
   - Verify documents list loads
   - Test document deletion

## Troubleshooting

### CORS Issues
If you encounter CORS errors, ensure your backend allows requests from your frontend domain:
```javascript
// Backend CORS configuration
app.use(cors({
  origin: 'http://localhost:3000', // Your frontend URL
  credentials: true
}));
```

### SSE Not Working
Ensure your backend properly implements Server-Sent Events:
- Set header: `Content-Type: text/event-stream`
- Format: `data: ${JSON.stringify(data)}\n\n`
- Keep connection alive with periodic heartbeats

### Styling Issues
If styles don't appear correctly:
1. Verify Tailwind CSS is properly configured
2. Check that the parent container has proper dimensions
3. Ensure no conflicting global styles

## Optional Enhancements

### Add Authentication
Wrap the component with your authentication context:
```tsx
const AuthenticatedChat = () => {
  const { token } = useAuth();
  
  // Pass token to API calls by modifying fetch headers in the component
  return <RubbenChat />;
};
```

### Add Error Boundaries
Wrap the component with an error boundary for production:
```tsx
<ErrorBoundary fallback={<ErrorFallback />}>
  <RubbenChat />
</ErrorBoundary>
```

### Add Loading State
Add a loading spinner while the component initializes:
```tsx
const [isReady, setIsReady] = useState(false);

useEffect(() => {
  // Check backend connectivity
  fetch(`${API_CONFIG.BASE_URL}/health`)
    .then(() => setIsReady(true))
    .catch(() => console.error('Backend not available'));
}, []);

return isReady ? <RubbenChat /> : <LoadingSpinner />;
```

## Support

For questions about:
- **Frontend Integration:** Check the component code comments
- **Backend Requirements:** Ensure all endpoints match the expected format
- **Styling:** Refer to Tailwind CSS documentation

## Notes

- The component is fully self-contained except for the two npm dependencies (lucide-react and framer-motion)
- All state management is handled internally
- The component is responsive and works on mobile devices
- File upload supports common document formats (PDF, DOC, DOCX, TXT, CSV, XLSX, XLS, PPT, PPTX)