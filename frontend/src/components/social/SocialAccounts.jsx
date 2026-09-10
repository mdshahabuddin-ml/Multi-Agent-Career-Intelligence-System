import { useState, useEffect } from "react";
import socialService from "../../services/socialService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function SocialAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const data = await socialService.listAccounts();
      setAccounts(data.accounts || []);
    } catch (err) {
      console.error("Failed to load accounts:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <Card title="Social Accounts">
      {accounts.length === 0 ? (
        <p className="text-gray-500 text-center py-4">No accounts connected</p>
      ) : (
        <div className="space-y-2">
          {accounts.map((account) => (
            <div key={account.id} className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <p className="font-medium">{account.platform}</p>
                <p className="text-sm text-gray-500">{account.account_name}</p>
              </div>
              <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">Connected</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default SocialAccounts;
