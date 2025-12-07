import { createContext, useState, useContext, useEffect, type ReactNode } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Array<{title: string; url: string}>;
}

interface ChatContextType {
  messages: Message[];
  addMessage: (message: Message) => void;
  clearMessages: () => void;
}

const ChatContext = createContext<ChatContextType | null>(null);

const INITIAL_MESSAGE: Message = {
  role: 'assistant',
  content: 'Hello! I\'m your medical information assistant. I can answer questions about tuberculosis, lung cancer, treatments, and general medical topics. How can I help you today?',
  timestamp: new Date()
};

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);

  // Listen for logout event to clear chat
  useEffect(() => {
    const handleClearChat = () => {
      setMessages([INITIAL_MESSAGE]);
    };
    
    window.addEventListener('clear-chat', handleClearChat);
    
    return () => {
      window.removeEventListener('clear-chat', handleClearChat);
    };
  }, []);

  const addMessage = (message: Message) => {
    setMessages(prev => [...prev, message]);
  };

  const clearMessages = () => {
    setMessages([INITIAL_MESSAGE]);
  };

  return (
    <ChatContext.Provider value={{ messages, addMessage, clearMessages }}>
      {children}
    </ChatContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useChat = (): ChatContextType => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within ChatProvider');
  }
  return context;
};

export type { Message };