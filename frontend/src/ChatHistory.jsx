import React, { useState, useEffect } from 'react';

const ChatHistory = ({ studentId, isOpen, onClose, onSelectChat, apiUrl = 'http://localhost:5000' }) => {
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchChatHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('[ChatHistory] Fetching for student:', studentId);
      console.log('[ChatHistory] API URL:', apiUrl);

      const response = await fetch(`${apiUrl}/api/chat-history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId })
      });

      console.log('[ChatHistory] Response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('[ChatHistory] Fetched data:', data);
        console.log('[ChatHistory] Number of chats:', data.chats?.length || 0);
        setChats(data.chats || []);
        if (data.chats && data.chats.length > 0) {
          console.log('[ChatHistory] First chat:', data.chats[0]);
        }
      } else {
        const errorText = await response.text();
        console.error('[ChatHistory] API error:', response.status, errorText);
        setError(`Failed to load chats (${response.status})`);
      }
    } catch (error) {
      console.error('[ChatHistory] Error fetching chat history:', error);
      setError(`Connection error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchChatHistory();
    }
  }, [isOpen, studentId]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div style={{
      position: 'fixed',
      left: 0,
      top: 0,
      width: 320,
      height: '100vh',
      background: 'white',
      borderRight: '1px solid #e5e7eb',
      boxShadow: '2px 0 8px rgba(0, 0, 0, 0.1)',
      transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
      transition: 'transform 0.3s ease-in-out',
      zIndex: 999,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: 16,
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
        color: 'white'
      }}>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>📋 Recent Chats</h3>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'white',
            fontSize: 20,
            cursor: 'pointer',
            padding: 0,
            width: 28,
            height: 28,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 6,
            transition: 'background-color 0.2s'
          }}
          onMouseOver={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'}
          onMouseOut={(e) => e.target.style.backgroundColor = 'transparent'}
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: 8
      }}>
        {error && (
          <div style={{ padding: 12, background: '#fee2e2', borderRadius: 8, margin: 8, color: '#991b1b', fontSize: 12 }}>
            ⚠️ {error}
          </div>
        )}
        {loading ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#64748b' }}>
            Loading chats...
          </div>
        ) : chats.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#64748b' }}>
            <p>No recent chats yet.</p>
            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 8 }}>
              Start learning and your last 7 chats will appear here!
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {chats.map((chat) => (
              <div
                key={chat.id}
                role="button"
                tabIndex={0}
                onClick={() => {
                  console.log('[ChatHistory] Clicked chat:', chat.id, 'topic:', chat.topic, 'content length:', chat.content?.length || 0);
                  onSelectChat(chat);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    console.log('[ChatHistory] Keyboard selected chat:', chat.id);
                    onSelectChat(chat);
                  }
                }}
                style={{
                  display: 'flex',
                  gap: 12,
                  padding: 12,
                  borderRadius: 10,
                  background: '#f9fafb',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  border: '1px solid #e5e7eb',
                  userSelect: 'none'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = '#eef5ff';
                  e.currentTarget.style.borderColor = '#3b82f6';
                  e.currentTarget.style.transform = 'translateX(4px)';
                  e.currentTarget.style.boxShadow = '0 2px 4px rgba(57, 154, 255, 0.2)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = '#f9fafb';
                  e.currentTarget.style.borderColor = '#e5e7eb';
                  e.currentTarget.style.transform = 'translateX(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: 24, flexShrink: 0 }}>📚</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontWeight: 600,
                    color: '#0f172a',
                    fontSize: 14,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    marginBottom: 4
                  }}>
                    {chat.topic}
                  </div>
                  <div style={{
                    fontSize: 12,
                    color: '#64748b',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    marginBottom: 4
                  }}>
                    {chat.preview || chat.content?.substring(0, 80) || 'No preview'}
                  </div>
                  <div style={{
                    fontSize: 11,
                    color: '#94a3b8',
                    display: 'flex',
                    gap: '8px'
                  }}>
                    <span>{chat.grade_level}</span>
                    <span>•</span>
                    <span>{chat.subject}</span>
                    <span>•</span>
                    <span>{formatDate(chat.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatHistory;
