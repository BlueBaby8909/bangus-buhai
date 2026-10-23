export default async function teardown() {
  try {
    await fetch("http://127.0.0.1:8019/__test/shutdown", { method: "POST" });
    await new Promise((resolve) => setTimeout(resolve, 1000));
  } catch {}
}
