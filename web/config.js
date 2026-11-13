/* 数据源开关：默认读本地 data/*.js；填了 Supabase 就改从云端拉 */
window.IB_CONFIG = {
  // 留空 = 用本地 data/*.js（离线可跑）
  supabaseUrl: "",
  supabaseKey: "",
  // 题目配图在 Storage 里的桶名
  imageBucket: "questions",
};
