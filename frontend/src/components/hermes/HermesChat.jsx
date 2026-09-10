import { useState } from "react";
import hermesService from "../../services/hermesService";
import Card from "../common/Card";
import Button from "../common/Button";

function HermesChat() {
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!message.trim()) return;

    const userMessage = { role: "user", content: message };
    setConversation([...conversation, userMessage]);
    setMessage("");
    setLoading(true);

    try {
      const result = await hermesService.executeTask(message);
      const agentMessage = {
        role: "agent",
        content: result.result?.status || "Task processed",
        agent: result.agent_id,
      };
      setConversation((prev) => [...prev, agentMessage]);
    } catch (err) {
      setConversation((prev) => [
        ...prev,
        { role: "agent", content: "Error processing request" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Hermes Chat">
      <div className="space-y-4">
        <div className="h-96 overflow-y-auto border rounded p-4 space-y-3">
          {conversation.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-xs px-4 py-2 rounded-lg ${
                  msg.role === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 px-4 py-2 rounded-lg">Thinking...</div>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask Hermes anything..."
            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <Button onClick={handleSend} loading={loading}>
            Send
          </Button>
        </div>
      </div>
    </Card>
  );
}

export default HermesChat;
