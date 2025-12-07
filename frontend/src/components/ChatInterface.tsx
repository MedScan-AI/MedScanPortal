import { useState, useRef, useEffect } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Array<{title: string; url: string}>;
}

interface ChatInterfaceProps {
  apiBaseUrl?: string;
}

const ChatInterface = ({ apiBaseUrl = 'http://localhost:8000/api' }: ChatInterfaceProps) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m your medical information assistant. I can answer questions about tuberculosis, lung cancer, treatments, and general medical topics. How can I help you today?',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      
      const response = await axios.post(
        `${apiBaseUrl}/rag/chat`,
        {
          message: userMessage.content,
          conversation_history: messages.slice(-10)
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        sources: response.data.sources || [],
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error: any) {
      console.error('Chat error:', error);
      
      const errorMessage: Message = {
        role: 'assistant',
        content: error.response?.data?.detail || 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
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
    // Auto-send after a brief delay
    setTimeout(() => {
      const inputElement = document.querySelector('input[type="text"]') as HTMLInputElement;
      if (inputElement) {
        inputElement.focus();
      }
    }, 100);
  };

  return (
    <div className="card h-100 d-flex flex-column" style={{ height: '600px' }}>
      {/* Header */}
      <div className="card-header bg-primary text-white">
        <h5 className="mb-0">🤖 Medical Information Assistant</h5>
        <small>Powered by AI • Evidence-based medical information</small>
      </div>

      {/* Messages */}
      <div className="card-body flex-grow-1 overflow-auto" style={{ maxHeight: '450px' }}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`mb-3 d-flex ${msg.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
          >
            <div
              className={`p-3 rounded ${
                msg.role === 'user'
                  ? 'bg-primary text-white'
                  : 'bg-light border'
              }`}
              style={{ maxWidth: '80%' }}
            >
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
              
              {/* Display sources if available */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-2 border-top">
                  <small className="text-muted fw-bold">📚 Sources:</small>
                  <ul className="mb-0 mt-1" style={{ fontSize: '0.85rem' }}>
                    {msg.sources.map((source, i) => (
                      <li key={i}>
                        <a 
                          href={source.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-decoration-none"
                        >
                          {source.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <small className={msg.role === 'user' ? 'text-white-50' : 'text-muted'}>
                {msg.timestamp.toLocaleTimeString()}
              </small>
            </div>
          </div>
        ))}

        {loading && (
          <div className="mb-3 d-flex justify-content-start">
            <div className="bg-light border p-3 rounded">
              <div className="spinner-border spinner-border-sm me-2" />
              <span>AI is thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="card-footer bg-white">
        {/* Suggested Questions */}
        <div className="mb-2">
          <small className="text-muted fw-bold">💡 Quick questions:</small>
          <div className="d-flex flex-wrap gap-1 mt-1">
            {[
              "What is tuberculosis?",
              "What are TB symptoms?",
              "How is lung cancer treated?",
              "What are TB medications?"
            ].map((q, i) => (
              <button
                key={i}
                className="btn btn-sm btn-outline-secondary"
                onClick={() => sendSuggestedQuestion(q)}
                disabled={loading}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <div className="input-group">
          <input
            type="text"
            className="form-control"
            placeholder="Ask about TB, lung cancer, treatments, symptoms..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            autoFocus
          />
          <button
            className="btn btn-primary"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            {loading ? (
              <>
                <span className="spinner-border spinner-border-sm me-1" />
                Sending
              </>
            ) : (
              'Send'
            )}
          </button>
        </div>
        <small className="text-muted">
          Press Enter to send
        </small>
      </div>
    </div>
  );
};

export default ChatInterface;