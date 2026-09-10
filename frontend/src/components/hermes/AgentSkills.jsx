import { useState, useEffect } from "react";
import skillService from "../../services/skillService";
import Card from "../common/Card";
import Loading from "../common/Loading";

function AgentSkills() {
  const [skills, setSkills] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [skillsData, statsData] = await Promise.all([
        skillService.listSkills(),
        skillService.getStats(),
      ]);
      setSkills(skillsData.skills || []);
      setStats(statsData);
    } catch (err) {
      console.error("Failed to load skills data:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Loading />;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Agent Skills</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-blue-600">{stats?.total_skills || 0}</p>
            <p className="text-sm text-gray-500">Registered Skills</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-green-600">{stats?.total_executions || 0}</p>
            <p className="text-sm text-gray-500">Total Executions</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-3xl font-bold text-purple-600">
              {stats?.successful || 0}
            </p>
            <p className="text-sm text-gray-500">Successful</p>
          </div>
        </Card>
      </div>

      <Card title="Skills">
        {skills.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No skills registered</p>
        ) : (
          <div className="space-y-2">
            {skills.map((skill) => (
              <div key={skill.name} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium">{skill.name}</p>
                  <p className="text-sm text-gray-500">{skill.description}</p>
                </div>
                <span className="text-sm text-gray-500">
                  {skill.execution_count} runs
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default AgentSkills;
