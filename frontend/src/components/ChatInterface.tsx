import { useState, useRef, useEffect } from 'react';
import { useChat, type Message } from '../contexts/ChatContext';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';

interface ChatInterfaceProps {
  apiBaseUrl?: string;
}

const ChatInterface = ({ apiBaseUrl = 'http://localhost:8000/api' }: ChatInterfaceProps) => {
  const { messages, addMessage } = useChat();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const pollJobStatus = async (jobId: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const token = localStorage.getItem('token');
      let pollCount = 0;
      const maxPolls = 150; // 5 minutes max

      pollingIntervalRef.current = setInterval(async () => {
        try {
          pollCount++;

          const response = await axios.get(
            `${apiBaseUrl}/rag/chat/status/${jobId}`,
            {
              headers: { 'Authorization': `Bearer ${token}` },
              timeout: 10000
            }
          );

          const { status, result, error } = response.data;

          if (status === 'completed' && result) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            
            const assistantMessage: Message = {
              role: 'assistant',
              content: result.response,
              sources: result.sources || [],
              timestamp: new Date()
            };
            
            addMessage(assistantMessage);
            resolve();
          } else if (status === 'failed') {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            throw new Error(error || 'AI processing failed');
          } else if (pollCount >= maxPolls) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            throw new Error('Request timed out. The AI is taking longer than expected.');
          }
          
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (error: any) {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          reject(error);
        }
      }, 2000); // Poll every 2 seconds
    });
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    addMessage(userMessage);
    setInput('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      
      // Start async job
      const startResponse = await axios.post(
        `${apiBaseUrl}/rag/chat/start`,
        {
          message: userMessage.content,
          conversation_history: messages.slice(-10)
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000
        }
      );

      const { job_id } = startResponse.data;
      
      // Poll for results
      await pollJobStatus(job_id);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      console.error('Chat error:', error);
      
      let errorMsg = 'Sorry, I encountered an error. Please try again.';
      
      if (error.response?.status === 504) {
        errorMsg = 'The AI is taking longer than expected to respond. Please try a simpler question or try again later.';
      } else if (error.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error.message) {
        errorMsg = error.message;
      }
      
      const errorMessage: Message = {
        role: 'assistant',
        content: errorMsg,
        timestamp: new Date()
      };
      
      addMessage(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const sendSuggestedQuestion = (question: string) => {
    setInput(question);
  };

  return (
    <div className="card border-0 shadow-sm d-flex flex-column" style={{ 
      borderRadius: '12px',
      height: '650px'
    }}>
      {/* Header */}
      <div className="card-header border-0 text-white" style={{
        background: 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
        padding: '1.5rem',
        borderRadius: '12px 12px 0 0'
      }}>
        <div className="d-flex align-items-center">
          <div style={{ fontSize: '1.75rem', marginRight: '0.75rem' }}>🤖</div>
          <div>
            <h5 className="mb-0 fw-bold">Medical Information Assistant</h5>
            <small style={{ opacity: 0.9 }}>Powered by AI • Evidence-based answers</small>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="card-body flex-grow-1 overflow-auto p-4" style={{ 
        background: '#f8f9fa',
        maxHeight: '450px'
      }}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`mb-4 d-flex ${msg.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
          >
            <div style={{ 
              maxWidth: '85%',
              animation: 'fadeIn 0.3s ease-in'
            }}>
              <div
                className={`p-3 ${msg.role === 'user' ? 'text-white' : ''}`}
                style={{
                  background: msg.role === 'user' 
                    ? 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)'
                    : 'white',
                  borderRadius: '12px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                }}
              >
                <div style={{ 
                  fontSize: '0.95rem',
                  lineHeight: '1.6'
                }} className={msg.role === 'assistant' ? 'markdown-content' : ''}>
                  {msg.role === 'assistant' ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : (
                    msg.content
                  )}
                </div>
                
                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 pt-3" style={{ 
                    borderTop: '1px solid rgba(0,0,0,0.1)',
                    fontSize: '0.85rem'
                  }}>
                    <div className="fw-semibold mb-2" style={{ color: '#6c757d' }}>
                      📚 Sources:
                    </div>
                    <div className="d-flex flex-column gap-1">
                      {msg.sources.slice(0, 5).map((source, i) => (
                        <a 
                          key={i}
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-decoration-none"
                          style={{ 
                            color: '#0f4c81',
                            fontSize: '0.85rem'
                          }}
                        >
                          {i + 1}. {source.title}
                        </a>
                      ))}
                    </div>
                    
                    <div className="mt-3 pt-3" style={{ 
                      borderTop: '1px solid rgba(0,0,0,0.05)',
                      fontSize: '0.75rem',
                      color: '#6c757d',
                      fontStyle: 'italic'
                    }}>
                      <strong>Note:</strong> This information is for educational purposes only. 
                      Always consult your healthcare provider for medical advice.
                    </div>
                  </div>
                )}
                
                <div className="mt-2">
                  <small style={{ 
                    opacity: 0.6,
                    fontSize: '0.75rem'
                  }}>
                    {msg.timestamp.toLocaleTimeString([], { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </small>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Simple Loader - No Progress Bar */}
        {loading && (
          <div className="mb-3 d-flex justify-content-start">
            <div className="bg-white p-3 shadow-sm" style={{ borderRadius: '12px' }}>
              <div className="d-flex align-items-center">
                <div className="spinner-border spinner-border-sm text-primary me-2" />
                <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>
                  AI is analyzing your question...
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="card-footer bg-white border-0" style={{ 
        padding: '1.5rem',
        borderRadius: '0 0 12px 12px'
      }}>
        {/* Suggested Questions */}
        <div className="mb-3">
          <small className="text-muted fw-semibold mb-2 d-block">💡 Suggested questions:</small>
          <div className="d-flex flex-wrap gap-2">
            {[
              "What are TB symptoms?",
              "How is lung cancer treated?",
              "What causes Tuberculosis?",
              "What is a chest X-ray?"
            ].map((q, i) => (
              <button
                key={i}
                className="btn btn-sm btn-outline-secondary"
                onClick={() => sendSuggestedQuestion(q)}
                disabled={loading}
                style={{
                  borderRadius: '20px',
                  fontSize: '0.8rem',
                  padding: '0.4rem 0.9rem',
                  fontWeight: 500,
                  border: '1.5px solid #dee2e6',
                  transition: 'all 0.2s'
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Input Box */}
        <div className="input-group input-group-lg">
          <input
            type="text"
            className="form-control"
            placeholder="Ask about symptoms, treatments, medications..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            autoFocus
            style={{
              borderRadius: '10px 0 0 10px',
              border: '2px solid #e0e6ed',
              padding: '0.75rem 1rem'
            }}
          />
          <button
            className="btn text-white fw-semibold"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            style={{
              background: loading || !input.trim() ? '#6c757d' : 'linear-gradient(135deg, #0f4c81 0%, #1a5f8a 100%)',
              border: 'none',
              borderRadius: '0 10px 10px 0',
              padding: '0.75rem 2rem',
              minWidth: '100px'
            }}
          >
            {loading ? 'Processing...' : 'Send'}
          </button>
        </div>
        <small className="text-muted d-block mt-2" style={{ fontSize: '0.8rem' }}>
          Press Enter to send
        </small>
      </div>

      {/* CSS */}
      <style>{`
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
          color: #2c3e50;
          margin-top: 1rem;
          margin-bottom: 0.5rem;
        }
        .markdown-content p {
          margin-bottom: 0.75rem;
        }
        .markdown-content ul, .markdown-content ol {
          margin-bottom: 0.75rem;
          padding-left: 1.5rem;
        }
        .markdown-content li {
          margin-bottom: 0.25rem;
        }
        .markdown-content strong {
          font-weight: 600;
          color: #2c3e50;
        }
        .markdown-content code {
          background: #f0f0f0;
          padding: 0.2rem 0.4rem;
          border-radius: 4px;
          font-size: 0.9em;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default ChatInterface;