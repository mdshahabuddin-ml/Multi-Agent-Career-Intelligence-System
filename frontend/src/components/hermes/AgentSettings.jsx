import { useState, useEffect } from "react";
import Card from "../common/Card";
import Loading from "../common/Loading";

function AgentSettings() {
  const [settings, setSettings] = useState({
    model: "gpt-4",
    temperature: 0.7,
    maxTokens: 4096,
    maxRetries: 3,
  });
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      // Placeholder for saving settings
      console.log("Saving settings:", settings);
    } catch (err) {
      console.error("Failed to save settings:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Agent Settings">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Model</label>
          <select
            value={settings.model}
            onChange={(e) => setSettings({ ...settings, model: e.target.value })}
            className="mt-1 block w-full border rounded-lg px-3 py-2"
          >
            <option value="gpt-4">GPT-4</option>
            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Temperature</label>
          <input
            type="number"
            value={settings.temperature}
            onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
            min="0"
            max="2"
            step="0.1"
            className="mt-1 block w-full border rounded-lg px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Max Tokens</label>
          <input
            type="number"
            value={settings.maxTokens}
            onChange={(e) => setSettings({ ...settings, maxTokens: parseInt(e.target.value) })}
            className="mt-1 block w-full border rounded-lg px-3 py-2"
          />
        </div>

        <button
          onClick={handleSave}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          {loading ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </Card>
  );
}

export default AgentSettings;
