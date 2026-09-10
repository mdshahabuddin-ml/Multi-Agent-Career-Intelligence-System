import { useState, useEffect } from "react";
import { contentCalendarService } from "../services";
import { format, subDays, startOfMonth, endOfMonth, subMonths } from "date-fns";

function AnalyticsDashboard() {
  const [dateRange, setDateRange] = useState("30d");
  const [selectedPlatform, setSelectedPlatform] = useState("all");
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [contentAnalytics, setContentAnalytics] = useState([]);
  const [platformComparison, setPlatformComparison] = useState({});
  const [contentTypeComparison, setContentTypeComparison] = useState({});
  const [topPosts, setTopPosts] = useState([]);

  const dateRanges = [
    { value: "7d", label: "Last 7 Days" },
    { value: "30d", label: "Last 30 Days" },
    { value: "90d", label: "Last 90 Days" },
    { value: "month", label: "This Month" },
    { value: "last_month", label: "Last Month" },
  ];

  const platforms = [
    { value: "all", label: "All Platforms" },
    { value: "youtube", label: "YouTube" },
    { value: "instagram", label: "Instagram" },
    { value: "facebook", label: "Facebook" },
    { value: "linkedin", label: "LinkedIn" },
    { value: "twitter", label: "Twitter/X" },
    { value: "tiktok", label: "TikTok" },
  ];

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      let startDate, endDate = new Date();
      const now = new Date();

      switch (dateRange) {
        case "7d":
          startDate = subDays(now, 7);
          break;
        case "30d":
          startDate = subDays(now, 30);
          break;
        case "90d":
          startDate = subDays(now, 90);
          break;
        case "month":
          startDate = startOfMonth(now);
          endDate = endOfMonth(now);
          break;
        case "last_month":
          startDate = startOfMonth(subMonths(now, 1));
          endDate = endOfMonth(subMonths(now, 1));
          break;
        default:
          startDate = subDays(now, 30);
      }

      const params = {
        start_date: format(startDate, "yyyy-MM-dd"),
        end_date: format(endDate, "yyyy-MM-dd"),
      };

      if (selectedPlatform !== "all") {
        params.platform = selectedPlatform;
      }

      const response = await contentCalendarService.getSummary(params);
      setSummary(response.data);

      // Process platform comparison
      if (response.data?.by_platform) {
        setPlatformComparison(response.data.by_platform);
      }

      // Process content type comparison
      if (response.data?.by_content_type) {
        setContentTypeComparison(response.data.by_content_type);
      }

      // Get top posts by engagement (from content calendar list with analytics)
      // For now, we'll use mock data or fetch from content list
      // TODO: Add proper top posts endpoint

    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [dateRange, selectedPlatform]);

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
  };

  const PLATFORM_COLORS = {
    youtube: "bg-red-500",
    instagram: "bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500",
    facebook: "bg-blue-600",
    linkedin: "bg-blue-700",
    twitter: "bg-sky-500",
    tiktok: "bg-gray-900",
  };

  const PLATFORM_ICONS = {
    youtube: "📺",
    instagram: "📷",
    facebook: "👍",
    linkedin: "💼",
    twitter: "🐦",
    tiktok: "🎵",
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-4 gap-4">
            <div className="h-24 bg-gray-200 rounded"></div>
            <div className="h-24 bg-gray-200 rounded"></div>
            <div className="h-24 bg-gray-200 rounded"></div>
            <div className="h-24 bg-gray-200 rounded"></div>
          </div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="text-gray-600 mt-1">Track your content performance across all platforms</p>
          </div>
          <div className="flex gap-3">
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {dateRanges.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {platforms.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Summary Cards */}
        {summary && (
          <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-500">Total Posts</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{summary.total_posts}</p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-500">Total Views</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{formatNumber(summary.total_views)}</p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-500">Total Engagement</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {formatNumber(summary.total_likes + summary.total_comments + summary.total_shares)}
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-500">Avg Engagement Rate</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{summary.avg_engagement_rate.toFixed(2)}%</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Platform Performance */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-lg border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Platform Performance</h3>
              </div>
              <div className="p-4 space-y-4">
                {Object.entries(platformComparison).map(([platform, data]) => (
                  <div key={platform} className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white ${PLATFORM_COLORS[platform] || "bg-gray-500"}`}>
                      {PLATFORM_ICONS[platform] || platform.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium capitalize">{platform}</span>
                        <span className="text-gray-500">{data.posts} posts</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden mt-1">
                        <div
                          className={`h-full ${PLATFORM_COLORS[platform] || "bg-gray-500"}`}
                          style={{ width: `${Math.min(data.views / (summary?.total_views || 1) * 100, 100)}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>{formatNumber(data.views)} views</span>
                        <span>{formatNumber(data.likes)} likes</span>
                        <span>{data.engagement_rate.toFixed(2)}% engagement</span>
                      </div>
                    </div>
                  </div>
                ))}
                {Object.keys(platformComparison).length === 0 && (
                  <p className="text-center text-gray-500 py-8">No data available for selected period</p>
                )}
              </div>
            </div>

            {/* Content Type Performance */}
            <div className="bg-white rounded-lg border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Content Type Performance</h3>
              </div>
              <div className="p-4 space-y-3">
                {Object.entries(contentTypeComparison).map(([type, data]) => (
                  <div key={type} className="flex items-center gap-3">
                    <span className="w-24 text-sm font-medium capitalize">{type}</span>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${Math.min(data.posts / (summary?.total_posts || 1) * 100, 100)}%` }}
                      ></div>
                    </div>
                    <span className="text-sm text-gray-500 w-20 text-right">{data.posts} posts</span>
                    <span className="text-sm text-gray-500 w-24 text-right">{data.engagement_rate.toFixed(2)}% engagement</span>
                  </div>
                ))}
                {Object.keys(contentTypeComparison).length === 0 && (
                  <p className="text-center text-gray-500 py-8">No data available</p>
                )}
              </div>
            </div>
          </div>

          {/* Top Posts & Quick Stats */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Top Performing Posts</h3>
              </div>
              <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
                {topPosts.length > 0 ? (
                  topPosts.map((post) => (
                    <div key={post.id} className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-full flex items-center justify-center text-white bg-blue-500 flex-shrink-0">
                          {PLATFORM_ICONS[post.platform] || "📝"}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{post.content_id ? `Post #${post.content_id}` : "Unknown"}</p>
                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                            <span className="capitalize">{post.platform}</span>
                            <span>{formatNumber(post.views)} views</span>
                            <span>{formatNumber(post.likes)} likes</span>
                            <span className="font-medium text-green-600">{post.engagement_rate.toFixed(2)}% engagement</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-center text-gray-500 py-8">No posts found</p>
                )}
              </div>
            </div>

            {/* Engagement Breakdown */}
            <div className="bg-white rounded-lg border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Engagement Breakdown</h3>
              </div>
              {summary && (
                <div className="p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Likes</span>
                    <span className="font-medium">{formatNumber(summary.total_likes)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Comments</span>
                    <span className="font-medium">{formatNumber(summary.total_comments)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Shares</span>
                    <span className="font-medium">{formatNumber(summary.total_shares)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Impressions</span>
                    <span className="font-medium">{formatNumber(summary.total_impressions)}</span>
                  </div>
                  <div className="pt-2 border-t border-gray-200">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Click-Through Rate</span>
                      <span className="font-medium">N/A</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
        </div>
      </div>
    </div>
  );
}

export default AnalyticsDashboard;