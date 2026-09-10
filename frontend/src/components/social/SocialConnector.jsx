import { useState } from "react";
import socialService from "../../services/socialService";
import Card from "../common/Card";
import Button from "../common/Button";

function SocialConnector() {
  const [platform, setPlatform] = useState("linkedin");
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      await socialService.connectAccount(platform);
    } catch (err) {
      console.error("Failed to connect:", err);
    } finally {
      setConnecting(false);
    }
  };

  return (
    <Card title="Connect Social Account">
      <div className="space-y-4">
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="w-full border rounded-lg px-3 py-2"
        >
          <option value="linkedin">LinkedIn</option>
          <option value="twitter">Twitter/X</option>
          <option value="instagram">Instagram</option>
          <option value="facebook">Facebook</option>
          <option value="youtube">YouTube</option>
        </select>
        <Button onClick={handleConnect} loading={connecting}>
          Connect {platform}
        </Button>
      </div>
    </Card>
  );
}

export default SocialConnector;
