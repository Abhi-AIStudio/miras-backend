import React, { useState, useEffect, useRef, useCallback } from "react";
import { 
  Trash2, 
  Plus, 
  ChevronDown, 
  FileText, 
  Lightbulb, 
  Globe, 
  Paperclip, 
  Send, 
  X 
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

// ==================== CONFIGURATION ====================
// Update these values to match your backend endpoints
const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || "http://localhost:8000",  // API backend URL
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

// ==================== TYPES ====================
interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  enhancedQuery?: string;
  sessionId?: string;
  isError?: boolean;
}

interface Session {
  id: string;
  title: string;
  started_at: string;
  last_message_at: string;
  message_count: number;
  is_active: boolean;
}

interface SessionMessage {
  id: string;
  query: string;
  enhanced_query: string | null;
  response: string;
  created_at: string;
}

interface DocumentInfo {
  id: string;
  name: string;
  type: string;
  size: number;
  size_formatted: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface DocumentsListResponse {
  success: boolean;
  documents: DocumentInfo[];
  total: number;
  error: string | null;
}

// ==================== UTILITIES ====================
function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

// ==================== MIRAS LOGO SVG ====================
const MiloLogoSVG = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <circle cx="12" cy="12" r="10" fill="#000"/>
    <path d="M8 8h2l1.5 3L13 8h2v8h-2v-4.5L11.5 14 10 11.5V16H8V8z" fill="#fff"/>
  </svg>
);

// ==================== PULSING DOT COMPONENT ====================
const PulsingDot = ({ color = 'green' }: { color?: 'green' | 'orange' }) => {
  const colorClasses = color === 'orange' 
    ? 'bg-orange-500' 
    : 'bg-green-500';
  
  return (
    <div className="relative">
      <div className={`w-1.5 h-1.5 ${colorClasses} rounded-full`}></div>
      <div className="absolute inset-0 -m-0.5">
        <div 
          className={`w-2.5 h-2.5 ${colorClasses} rounded-full animate-pulse`}
        ></div>
      </div>
    </div>
  );
};

// ==================== BUTTON COMPONENT ====================
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

const Button: React.FC<ButtonProps> = ({ 
  variant = 'default', 
  size = 'md', 
  className = '', 
  children, 
  ...props 
}) => {
  const baseClasses = "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50";
  
  const variantClasses = {
    default: "bg-black text-white hover:bg-gray-800",
    outline: "border border-gray-300 bg-white hover:bg-gray-50",
    ghost: "hover:bg-gray-100"
  };
  
  const sizeClasses = {
    sm: "h-8 px-3 text-xs rounded-md",
    md: "h-9 px-4 py-2 text-sm rounded-md",
    lg: "h-10 px-8 text-base rounded-md"
  };
  
  return (
    <button
      className={cn(baseClasses, variantClasses[variant], sizeClasses[size], className)}
      {...props}
    >
      {children}
    </button>
  );
};

// ==================== CHAT INPUT COMPONENT ====================
const PLACEHOLDERS = [
  "Analyze our fund strategy against LP preferences",
  "Find LPs that have invested in similar European funds",
  "What's our strongest investment thesis match?",
];

interface AIChatInputProps {
  onSend?: (message: string, files?: File[]) => void;
  disabled?: boolean;
  placeholder?: string;
}

const AIChatInput: React.FC<AIChatInputProps> = ({ onSend, disabled = false, placeholder }) => {
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [showPlaceholder, setShowPlaceholder] = useState(true);
  const [isActive, setIsActive] = useState(false);
  const [thinkActive, setThinkActive] = useState(false);
  const [deepSearchActive, setDeepSearchActive] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cycle placeholder text
  useEffect(() => {
    if (isActive || inputValue) return;

    const interval = setInterval(() => {
      setTimeout(() => {
        setShowPlaceholder(false);
        setTimeout(() => {
          setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDERS.length);
          setShowPlaceholder(true);
        }, 400);
      }, 2500);
    }, 3500);

    return () => clearInterval(interval);
  }, [isActive, inputValue]);

  // Close input when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        if (!inputValue) setIsActive(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [inputValue]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      setAttachedFiles(Array.from(files));
    }
  };

  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSend = () => {
    if ((inputValue.trim() || attachedFiles.length > 0) && onSend) {
      onSend(inputValue.trim(), attachedFiles);
      setInputValue('');
      setAttachedFiles([]);
      setIsActive(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const containerVariants: any = {
    collapsed: {
      height: attachedFiles.length > 0 ? 96 : 56,
      boxShadow: "0 2px 8px 0 rgba(0,0,0,0.08)",
      transition: { type: "spring", stiffness: 120, damping: 18 },
    },
    expanded: {
      height: attachedFiles.length > 0 ? 168 : 128,
      boxShadow: "0 8px 32px 0 rgba(0,0,0,0.16)",
      transition: { type: "spring", stiffness: 120, damping: 18 },
    },
  };

  const placeholderContainerVariants = {
    initial: {},
    animate: { transition: { staggerChildren: 0.025 } },
    exit: { transition: { staggerChildren: 0.015, staggerDirection: -1 } },
  };

  const letterVariants: any = {
    initial: {
      opacity: 0,
      filter: "blur(12px)",
      y: 10,
    },
    animate: {
      opacity: 1,
      filter: "blur(0px)",
      y: 0,
      transition: {
        opacity: { duration: 0.25 },
        filter: { duration: 0.4 },
        y: { type: "spring", stiffness: 80, damping: 20 },
      },
    },
    exit: {
      opacity: 0,
      filter: "blur(12px)",
      y: -10,
      transition: {
        opacity: { duration: 0.2 },
        filter: { duration: 0.3 },
        y: { type: "spring", stiffness: 80, damping: 20 },
      },
    },
  };

  return (
    <motion.div
      ref={wrapperRef}
      className="w-full"
      variants={containerVariants}
      animate={isActive || inputValue ? "expanded" : "collapsed"}
      initial="collapsed"
      style={{ overflow: "hidden", borderRadius: 32, background: "#fff" }}
      onClick={() => setIsActive(true)}
    >
      <div className="flex flex-col items-stretch w-full h-full">
        {/* Attached Files Display */}
        {attachedFiles.length > 0 && (
          <div className="px-4 pt-2 pb-1">
            <div className="flex flex-wrap gap-2">
              {attachedFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-full text-sm"
                >
                  <span className="text-gray-700">{file.name}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    className="p-0.5 hover:bg-gray-200 rounded-full transition"
                    type="button"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Input Row */}
        <div className="flex items-center gap-2 p-2 rounded-full bg-white w-full h-14">
          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls,.ppt,.pptx"
          />
          
          <button
            className="p-2.5 rounded-full hover:bg-gray-100 transition flex items-center justify-center"
            title="Attach file"
            type="button"
            tabIndex={-1}
            onClick={() => fileInputRef.current?.click()}
          >
            <Paperclip size={20} />
          </button>

          {/* Text Input & Placeholder */}
          <div className="relative flex-1 flex items-center h-full">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="flex-1 border-0 outline-0 rounded-md text-base bg-transparent w-full font-normal h-full"
              style={{ position: "relative", zIndex: 1 }}
              onFocus={() => setIsActive(true)}
              disabled={disabled}
              placeholder={placeholder}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && (inputValue.trim() || attachedFiles.length > 0)) {
                  e.preventDefault();
                  handleSend();
                }
              }}
            />
            <div className="absolute left-0 top-0 w-full h-full pointer-events-none flex items-center">
              <AnimatePresence mode="wait">
                {showPlaceholder && !isActive && !inputValue && (
                  <motion.span
                    key={placeholderIndex}
                    className="text-gray-400 select-none pointer-events-none"
                    style={{
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      zIndex: 0,
                    }}
                    variants={placeholderContainerVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                  >
                    {PLACEHOLDERS[placeholderIndex]
                      .split("")
                      .map((char, i) => (
                        <motion.span
                          key={i}
                          variants={letterVariants}
                          style={{ display: "inline-block" }}
                        >
                          {char === " " ? "\u00A0" : char}
                        </motion.span>
                      ))}
                  </motion.span>
                )}
              </AnimatePresence>
            </div>
          </div>

          <button
            className="flex items-center gap-1 bg-black hover:bg-zinc-700 text-white p-2.5 rounded-full font-medium justify-center disabled:opacity-50 disabled:cursor-not-allowed"
            title="Send"
            type="button"
            tabIndex={-1}
            disabled={disabled || (!inputValue.trim() && attachedFiles.length === 0)}
            onClick={handleSend}
          >
            <Send size={18} />
          </button>
        </div>

        {/* Expanded Controls */}
        <motion.div
          className="w-full flex justify-start px-4 items-center text-sm"
          variants={{
            hidden: {
              opacity: 0,
              y: 20,
              pointerEvents: "none" as const,
              transition: { duration: 0.25 },
            },
            visible: {
              opacity: 1,
              y: 0,
              pointerEvents: "auto" as const,
              transition: { duration: 0.35, delay: 0.08 },
            },
          }}
          initial="hidden"
          animate={isActive || inputValue ? "visible" : "hidden"}
          style={{ marginTop: 8 }}
        >
          <div className="flex gap-3 items-center">
            {/* Think Toggle */}
            <button
              className={cn(
                "flex items-center gap-1 px-4 py-2 rounded-full transition-all font-medium group",
                thinkActive
                  ? "bg-blue-600/10 outline outline-blue-600/60 text-blue-950"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
              title="Think"
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setThinkActive((a) => !a);
              }}
            >
              <Lightbulb
                className="group-hover:fill-yellow-300 transition-all"
                size={18}
              />
              Think
            </button>

            {/* Deep Search Toggle */}
            <motion.button
              className={cn(
                "flex items-center px-4 gap-1 py-2 rounded-full transition font-medium whitespace-nowrap overflow-hidden justify-start",
                deepSearchActive
                  ? "bg-blue-600/10 outline outline-blue-600/60 text-blue-950"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
              title="Deep Search"
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setDeepSearchActive((a) => !a);
              }}
              initial={false}
              animate={{
                width: deepSearchActive ? 125 : 36,
                paddingLeft: deepSearchActive ? 8 : 9,
              }}
            >
              <div className="flex-1">
                <Globe size={18} />
              </div>
              <motion.span
                className="pb-[2px]"
                initial={false}
                animate={{
                  opacity: deepSearchActive ? 1 : 0,
                }}
              >
                Deep Search
              </motion.span>
            </motion.button>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};

// ==================== CUSTOM HOOK FOR MIRAS QUERY ====================
interface UseMiloQueryReturn {
  askQuestion: (query: string, sessionId?: string | null) => Promise<void>;
  answer: string;
  loading: boolean;
  error: string | null;
  phase: string;
  sessionId: string | null;
  enhancedQuery: string | null;
  citations: any[];
  validationThinking: string;
  validationResult: any;
}

const useMiloQuery = (): UseMiloQueryReturn => {
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [enhancedQuery, setEnhancedQuery] = useState<string | null>(null);
  const [citations, setCitations] = useState<any[]>([]);
  const [validationThinking, setValidationThinking] = useState('');
  const [validationResult, setValidationResult] = useState<any>(null);

  const askQuestion = useCallback(async (query: string, currentSessionId?: string | null) => {
    setLoading(true);
    setAnswer('');
    setError(null);
    setPhase('routing');
    setEnhancedQuery(null);
    setCitations([]);
    setValidationThinking('');
    setValidationResult(null);

    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.SEARCH}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            mode: 'hybrid',
            stream: true,
            session_id: currentSessionId !== undefined ? currentSessionId : sessionId
          })
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim() === '') continue;
          if (!line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));
            
            switch (data.phase) {
              case 'routing':
                setPhase('Analyzing your question...');
                break;
              case 'search':
                setPhase('Searching knowledge base...');
                break;
              case 'synthesis':
                setPhase('Preparing answer...');
                break;
              case 'session_created':
              case 'session_continued':
                setSessionId(data.session_id);
                break;
              case 'query_enhanced':
                setEnhancedQuery(data.enhanced_query);
                break;
              case 'answer':
                setAnswer(prev => prev + data.content);
                setPhase('');
                break;
              case 'citations':
                setCitations(data.citations || []);
                break;
              case 'validation_start':
                setPhase('Validating response...');
                setValidationThinking('');
                break;
              case 'validation_thinking':
                setValidationThinking(data.content);  // Overwrite instead of append
                setPhase('Thinking: ' + data.content.substring(0, 50) + '...');
                break;
              case 'validation_complete':
                setValidationResult(data.validation);
                setPhase('');
                break;
              case 'complete':
                setLoading(false);
                break;
              case 'error':
                throw new Error(data.error);
            }
          } catch (e) {
            console.warn('Failed to parse SSE data:', e);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setLoading(false);
    }
  }, [sessionId]);

  return { askQuestion, answer, loading, error, phase, sessionId, enhancedQuery, citations, validationThinking, validationResult };
};

// ==================== MAIN RUBBEN CHAT COMPONENT ====================
const MiloChat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const { askQuestion, answer, loading, error, phase, sessionId, enhancedQuery, citations, validationThinking, validationResult } = useMiloQuery();
  const [currentUserMessage, setCurrentUserMessage] = useState('');
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [documentsOpen, setDocumentsOpen] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);

  // Fetch sessions
  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.SESSIONS}?limit=20&active_only=false`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  // Fetch documents
  const fetchDocuments = async () => {
    setIsLoadingDocuments(true);
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DOCUMENTS}`);
      const data: DocumentsListResponse = await response.json();
      
      if (data.success) {
        setDocuments(data.documents);
      } else {
        console.error('Failed to fetch documents:', data.error);
      }
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  // Delete document
  const deleteDocument = async (documentId: string, documentName: string) => {
    const confirmed = window.confirm(`Are you sure you want to delete "${documentName}"?`);
    if (!confirmed) return;

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DELETE_DOCUMENT(documentId)}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        setMessages(prev => [...prev, {
          id: `system-${Date.now()}`,
          type: 'system',
          content: `Document "${documentName}" deleted successfully`,
          timestamp: new Date()
        }]);
        
        await fetchDocuments();
      } else if (response.status === 404) {
        alert('Document not found');
      } else {
        const error = await response.json();
        alert(`Failed to delete document: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('Failed to delete document');
    }
  };

  // Fetch initial data
  useEffect(() => {
    fetchSessions();
    fetchDocuments();
  }, []);

  // Handle document ingestion
  const handleDocumentIngestion = async (files: File[], userInstructions: string = '') => {
    const formData = new FormData();
    
    files.forEach(file => {
      formData.append('files', file);
    });
    
    if (userInstructions) {
      formData.append('user_instructions', userInstructions);
    }
    
    let processingMessageId: string | null = null;
    
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.INGEST}`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const successfulFiles: string[] = [];
      
      if (!reader) {
        throw new Error('No response body');
      }
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              switch (data.type) {
                case 'progress':
                  processingMessageId = `system-processing-${Date.now()}`;
                  setMessages(prev => [...prev, {
                    id: processingMessageId!,
                    type: 'system',
                    content: data.message,
                    timestamp: new Date()
                  }]);
                  break;
                  
                case 'file_complete':
                  const cleanMessage = data.message
                    .replace('✅ ', '')
                    .replace('ingested successfully', 'processed successfully');
                  
                  if (processingMessageId) {
                    setMessages(prev => prev.map(msg => 
                      msg.id === processingMessageId 
                        ? { ...msg, content: cleanMessage }
                        : msg
                    ));
                  } else {
                    setMessages(prev => [...prev, {
                      id: `system-${Date.now()}-${Math.random()}`,
                      type: 'system',
                      content: cleanMessage,
                      timestamp: new Date()
                    }]);
                  }
                  
                  if (data.filename) {
                    successfulFiles.push(data.filename);
                  }
                  break;
                  
                case 'file_failed':
                  const errorMessage = data.message.replace('❌ ', '');
                  setMessages(prev => [...prev, {
                    id: `system-${Date.now()}-${Math.random()}`,
                    type: 'system',
                    content: errorMessage,
                    timestamp: new Date(),
                    isError: true
                  }]);
                  break;
                  
                case 'file_summary':
                  setMessages(prev => [...prev, {
                    id: `system-${Date.now()}-${Math.random()}`,
                    type: 'assistant',
                    content: `Document Summary:\n\n${data.summary}`,
                    timestamp: new Date()
                  }]);
                  break;
                  
                case 'batch_complete':
                  break;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
      
      await fetchDocuments();
      
    } catch (error) {
      console.error('Error during document ingestion:', error);
      setMessages(prev => [...prev, {
        id: `system-${Date.now()}`,
        type: 'system',
        content: `Failed to upload documents: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
        isError: true
      }]);
    }
  };

  const handleSendMessage = async (message: string, files?: File[]) => {
    if (!message.trim() && (!files || files.length === 0)) return;
    
    if (files && files.length > 0) {
      if (message.trim()) {
        const userMessage: Message = {
          id: Date.now().toString(),
          type: 'user',
          content: message,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, userMessage]);
      }
      
      await handleDocumentIngestion(files, message);
      
    } else {
      const userMessage: Message = {
        id: Date.now().toString(),
        type: 'user',
        content: message,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, userMessage]);
      setCurrentUserMessage(message);
      
      await askQuestion(message, currentSessionId);
    }
  };

  // Update messages when we get a new answer
  useEffect(() => {
    if (answer && currentUserMessage) {
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.type === 'assistant') {
          return prev.slice(0, -1).concat({
            ...lastMessage,
            content: answer,
            sessionId: sessionId || undefined
          });
        } else {
          return [...prev, {
            id: Date.now().toString(),
            type: 'assistant',
            content: answer,
            timestamp: new Date(),
            sessionId: sessionId || undefined
          }];
        }
      });
    }
  }, [answer, currentUserMessage, sessionId]);

  // Remove validation thinking from messages when validation completes
  // (We only show thinking in the bottom status, not in chat)

  // Handle validation result display
  useEffect(() => {
    if (validationResult) {
      const facts = validationResult.facts_checked || [];
      const queryAnswered = validationResult.query_answered;
      
      let resultContent = '✅ Validation Complete\n\n';
      
      if (queryAnswered) {
        resultContent += '✓ Query answered\n\n';
      } else {
        resultContent += '✗ Query not fully answered\n\n';
      }
      
      if (facts.length > 0) {
        resultContent += 'Fact Checking:\n';
        facts.forEach((fact: any) => {
          const icon = fact.verified ? '✅' : '❌';
          resultContent += `${icon} ${fact.fact}\n`;
        });
      }
      
      const validationMessage: Message = {
        id: 'validation-result',
        type: 'system',
        content: resultContent,
        timestamp: new Date()
      };
      
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== 'validation-thinking' && m.id !== 'validation-result');
        return [...filtered, validationMessage];
      });
    }
  }, [validationResult]);

  // Handle citations display
  useEffect(() => {
    if (citations && citations.length > 0) {
      const citationContent = 'Sources:\n' + 
        citations.map((c: any) => `[${c.number}] ${c.doc_name} (Page ${c.page})`).join('\n');
      
      const citationMessage: Message = {
        id: 'citations',
        type: 'system',
        content: citationContent,
        timestamp: new Date()
      };
      
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== 'citations');
        const assistantMsgIndex = prev.findIndex(m => m.type === 'assistant');
        if (assistantMsgIndex >= 0) {
          const newMessages = [...prev];
          // Insert citations after assistant message
          newMessages.splice(assistantMsgIndex + 1, 0, citationMessage);
          return newMessages;
        }
        return prev;
      });
    }
  }, [citations]);

  // Update current session ID
  useEffect(() => {
    if (sessionId) {
      setCurrentSessionId(sessionId);
      if (!loading && answer) {
        setTimeout(() => {
          fetchSessions();
        }, 1000);
      }
    }
  }, [sessionId, loading, answer]);

  // Update user message with enhanced query
  useEffect(() => {
    if (enhancedQuery && messages.length > 0) {
      const lastUserMessage = [...messages].reverse().find(m => m.type === 'user');
      if (lastUserMessage) {
        setMessages(prev => prev.map(msg => 
          msg.id === lastUserMessage.id 
            ? { ...msg, enhancedQuery } 
            : msg
        ));
      }
    }
  }, [enhancedQuery, messages]);

  const handleSessionClick = async (session: Session) => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.SESSION_MESSAGES(session.id)}`);
      if (response.ok) {
        const sessionMessages: SessionMessage[] = await response.json();
        
        const chatMessages: Message[] = [];
        sessionMessages.forEach((msg) => {
          chatMessages.push({
            id: `${msg.id}-user`,
            type: 'user',
            content: msg.query,
            timestamp: new Date(msg.created_at),
            enhancedQuery: msg.enhanced_query || undefined,
            sessionId: session.id
          });
          chatMessages.push({
            id: `${msg.id}-assistant`,
            type: 'assistant',
            content: msg.response,
            timestamp: new Date(msg.created_at),
            sessionId: session.id
          });
        });
        
        setMessages(chatMessages);
        setCurrentSessionId(session.id);
      }
    } catch (error) {
      console.error('Error loading session messages:', error);
    }
  };

  const isSessionActive = (lastMessageAt: string) => {
    const diff = Date.now() - new Date(lastMessageAt).getTime();
    return diff < 30 * 60 * 1000; // 30 minutes
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="absolute inset-0 flex">
      {/* Left Sidebar - Wider now */}
      <div className="w-96 border-r bg-white flex flex-col">
        {/* Past Conversations - Takes 70% of sidebar */}
        <div className="flex-1 p-6 overflow-y-auto" style={{ maxHeight: '70%' }}>
          <h2 className="text-lg font-semibold mb-4">Past Conversations</h2>
          <div className="space-y-2">
            {isLoadingSessions ? (
              <p className="text-sm text-gray-500">Loading conversations...</p>
            ) : sessions.length === 0 ? (
              <p className="text-sm text-gray-500">No conversations yet. Start by asking a question!</p>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.id}
                  className={cn(
                    "group relative p-3 rounded-lg border bg-white cursor-pointer transition-all hover:shadow-sm",
                    session.id === currentSessionId
                      ? "border-black bg-gray-50"
                      : "border-gray-200 hover:bg-gray-50"
                  )}
                  onClick={() => handleSessionClick(session)}
                >
                  <button
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 rounded"
                    onClick={async (e) => {
                      e.stopPropagation();
                      try {
                        const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DELETE_SESSION(session.id)}`, {
                          method: 'DELETE',
                        });
                        if (response.ok) {
                          setSessions(prev => prev.filter(s => s.id !== session.id));
                          if (currentSessionId === session.id) {
                            setMessages([]);
                            setCurrentSessionId(null);
                          }
                        }
                      } catch (error) {
                        console.error('Error deleting session:', error);
                      }
                    }}
                  >
                    <Trash2 className="h-3 w-3 text-gray-500 hover:text-red-500" />
                  </button>
                  <div className="flex items-start justify-between pr-6">
                    <h4 className="font-medium text-sm pr-2 flex-1">{session.title}</h4>
                    {isSessionActive(session.last_message_at) && (
                      <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5" title="Active session" />
                    )}
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <p className="text-xs text-gray-500">{formatDate(session.last_message_at)}</p>
                    <span className="text-xs text-gray-400">{session.message_count} messages</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        
        {/* Documents and Sources Section - Takes 30% at bottom */}
        <div className="p-6 space-y-4 border-t" style={{ minHeight: '30%' }}>
          {/* Documents Dropdown */}
          <div className="relative">
            <button
              onClick={() => setDocumentsOpen(!documentsOpen)}
              className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span>Documents ({documents.length})</span>
              </div>
              <ChevronDown className={cn(
                "h-4 w-4 transition-transform",
                documentsOpen && "rotate-180"
              )} />
            </button>
            
            {documentsOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-2 max-h-40 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg z-10">
                {isLoadingDocuments ? (
                  <div className="p-3 text-sm text-gray-500">Loading documents...</div>
                ) : documents.length === 0 ? (
                  <div className="p-3 text-sm text-gray-500">No documents uploaded yet</div>
                ) : (
                  <div className="py-1">
                    {documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="px-3 py-1.5 hover:bg-gray-50 flex items-center justify-between group"
                      >
                        <div className="flex-1 min-w-0">
                          <span className="text-sm text-gray-700 truncate block">
                            {doc.name.replace(/\.[^/.]+$/, "")}
                          </span>
                          {doc.status !== 'completed' && (
                            <span className="text-xs text-amber-600">
                              {doc.status}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteDocument(doc.id, doc.name);
                          }}
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-100 rounded ml-2"
                          title="Delete document"
                        >
                          <Trash2 className="h-3 w-3 text-red-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sources Section */}
          <div className="mt-auto">
            <h3 className="font-medium mb-3">Sources</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Salesforce</span>
                <PulsingDot color="orange" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Internal Datastore</span>
                <PulsingDot color="green" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area - Expanded to fill remaining space */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Header */}
        <div className="border-b p-4">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold">Ask Milo</h1>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setMessages([]);
                setCurrentSessionId(null);
                setCurrentUserMessage('');
              }}
              className="flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </div>
        </div>

        {/* Chat Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <h2 className="text-2xl font-bold text-gray-800 mb-3">Milo AI Assistant</h2>
              <p className="text-gray-600 text-center max-w-md">
                Ask me anything about your fund, investors, or strategy
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex",
                    message.type === 'user' ? "justify-end" : "justify-start"
                  )}
                >
                  <div
                    className={cn(
                      "max-w-[70%] rounded-lg p-4",
                      message.type === 'user'
                        ? "bg-black text-white"
                        : message.type === 'system'
                        ? "bg-gray-100"
                        : "bg-white border border-gray-200"
                    )}
                  >
                    <div className="text-sm whitespace-pre-wrap text-left">
                      {message.type === 'system' ? (
                        <div className="flex items-center gap-2">
                          {message.content.includes('Processing') ? (
                            <>
                              <MiloLogoSVG />
                              <p className="text-sm text-gray-600 italic">{message.content}</p>
                            </>
                          ) : message.content.includes('✅') ? (
                            <>
                              <MiloLogoSVG />
                              <p className="text-sm text-green-600">{message.content}</p>
                            </>
                          ) : message.isError || message.content.includes('❌') ? (
                            <>
                              <MiloLogoSVG />
                              <p className="text-sm text-red-600">{message.content}</p>
                            </>
                          ) : (
                            <>
                              <MiloLogoSVG />
                              <p className="text-sm text-gray-600">{message.content}</p>
                            </>
                          )}
                        </div>
                      ) : message.type === 'assistant' ? (
                        <>
                          {message.content.split('\n').map((line, index) => (
                            <React.Fragment key={index}>
                              {line.trim().endsWith(':') ? (
                                <strong>{line}</strong>
                              ) : (
                                line
                              )}
                              {index < message.content.split('\n').length - 1 && '\n'}
                            </React.Fragment>
                          ))}
                          {loading && messages[messages.length - 1].id === message.id && (
                            <span className="inline-block animate-pulse ml-1">...</span>
                          )}
                        </>
                      ) : (
                        message.content
                      )}
                    </div>
                    {message.type === 'user' && message.enhancedQuery && (
                      <p className="text-xs mt-2 opacity-70" title="Query enhanced for context">
                        ↳ {message.enhancedQuery}
                      </p>
                    )}
                  </div>
                </div>
              ))}
              
              {/* Loading states */}
              {loading && phase && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg p-4 max-w-[80%]">
                    <div className="flex items-center gap-2">
                      <MiloLogoSVG />
                      <p className="text-sm text-gray-600 italic">{phase}</p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Error state */}
              {error && (
                <div className="flex justify-center">
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-600">Error: {error}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t p-4">
          <div className="max-w-3xl mx-auto">
            <AIChatInput
              onSend={handleSendMessage}
              disabled={loading}
              placeholder=""
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default MiloChat;