import { useState, useEffect } from "react";
import Card from "../common/Card";
import Loading from "../common/Loading";

function CampaignManager() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCampaigns();
  }, []);

  const loadCampaigns = async () => {
    try {
      setCampaigns([]);
    } catch (err) {
      console.error("Failed to load campaigns:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Campaign Manager">
      {campaigns.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No campaigns</p>
      ) : (
        <div className="space-y-2">
          {campaigns.map((campaign) => (
            <div key={campaign.id} className="p-3 border rounded-lg">
              <p className="font-medium">{campaign.name}</p>
              <p className="text-sm text-gray-500">{campaign.status}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default CampaignManager;
