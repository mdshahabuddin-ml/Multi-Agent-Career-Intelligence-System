import { useState } from "react";
import Card from "../common/Card";
import Button from "../common/Button";

function ContentEditor({ content, onSave }) {
  const [title, setTitle] = useState(content?.title || "");
  const [body, setBody] = useState(content?.body || "");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({ title, body });
    } catch (err) {
      console.error("Failed to save:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title="Edit Content">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-1 block w-full border rounded-lg px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Body</label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={10}
            className="mt-1 block w-full border rounded-lg px-3 py-2"
          />
        </div>
        <Button onClick={handleSave} loading={saving}>
          Save Changes
        </Button>
      </div>
    </Card>
  );
}

export default ContentEditor;
