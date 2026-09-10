import { useState } from "react";
import contentService from "../../services/contentService";
import Card from "../common/Card";
import Button from "../common/Button";

function ContentGenerator() {
  const [prompt, setPrompt] = useState("");
  const [generated, setGenerated] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    try {
      const result = await contentService.createContent(prompt, "post", prompt);
      setGenerated(result.title || "Content generated");
    } catch (err) {
      console.error("Failed to generate content:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Content Generator">
      <div className="space-y-4">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe what content you want to create..."
          rows={4}
          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        <Button onClick={handleGenerate} loading={loading}>
          Generate Content
        </Button>
        {generated && (
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="font-medium">Generated:</p>
            <p className="text-gray-700 mt-2">{generated}</p>
          </div>
        )}
      </div>
    </Card>
  );
}

export default ContentGenerator;
