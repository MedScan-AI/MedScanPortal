import { useState, useRef, useEffect } from 'react';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  apiBaseUrl?: string;
}

const ChatInterface = ({ apiBaseUrl = 'http://localhost:8000/api' }: ChatInterfaceProps) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m your medical information assistant. You can ask me questions about tuberculosis, lung cancer, treatments, and general medical topics. How can I help you today?',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
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
      // Get auth token
      const token = localStorage.getItem('token');
      
      // Send to backend
      const response = await axios.post(
        `${apiBaseUrl}/rag/chat`,
        {
          message: userMessage.content,
          conversation_history: messages.slice(-10) // Last 10 messages for context
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
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
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

  return (
    <div className="card h-100 d-flex flex-column" style={{ height: '600px' }}>
      {/* Header */}
      <div className="card-header bg-primary text-white">
        <h5 className="mb-0">🤖 Medical Information Assistant</h5>
        <small>Ask questions about TB, lung cancer, treatments, and more</small>
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
              style={{ maxWidth: '75%' }}
            >
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
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
              <span>Thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="card-footer">
        <div className="input-group">
          <input
            type="text"
            className="form-control"
            placeholder="Ask a question about tuberculosis, lung cancer, treatments..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
        <small className="text-muted">
          Press Enter to send • Shift+Enter for new line
        </small>
      </div>
    </div>
  );
};

export default ChatInterface;