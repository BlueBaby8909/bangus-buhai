import { useEffect, useRef, useState } from "react";
import { configureApi, request, message } from "./api";
import { Auth } from "./auth-context";
export function AuthProvider({ children }) {
  const [operator, setOperator] = useState(null);
  const [hatchery, setHatchery] = useState("");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const epoch = useRef(0);
  function clear(error) {
    epoch.current++;
    setOperator(null);
    setHatchery("");
    setNotice(
      error?.status === 403
        ? "Your access changed. Sign in again or contact the owner."
        : "Your session ended. Please sign in again.",
    );
    configureApi("", clear);
  }
  function accept(data) {
    configureApi(data.csrf_token, clear);
    setOperator(data);
    setHatchery((previous) =>
      data.hatcheries.some((h) => h.id === previous)
        ? previous
        : data.hatcheries[0]?.id || "",
    );
  }
  useEffect(() => {
    const controller = new AbortController();
    configureApi("", clear);
    request("/me", { passive: true, signal: controller.signal })
      .then(accept)
      .catch((error) => {
        if (error.name !== "AbortError" && ![401, 403].includes(error.status))
          setNotice("The service is unavailable. You can retry signing in.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!operator) return;
    const controller = new AbortController();
    const check = () => {
      if (document.visibilityState === "visible") {
        const generation = epoch.current;
        request("/me", { passive: true, signal: controller.signal })
          .then((data) => {
            if (generation === epoch.current && !controller.signal.aborted)
              accept(data);
          })
          .catch(() => {});
      }
    };
    const timer = setInterval(check, 30000);
    document.addEventListener("visibilitychange", check);
    return () => {
      clearInterval(timer);
      controller.abort();
      document.removeEventListener("visibilitychange", check);
    };
  }, [operator]);
  async function login(email, password) {
    const generation = ++epoch.current;
    const data = await request("/auth/login", {
      method: "POST",
      body: { email, password },
    });
    if (generation === epoch.current) {
      accept(data);
      setNotice("");
    }
  }
  async function logout() {
    try {
      await request("/auth/logout", { method: "POST" });
    } catch (error) {
      setNotice("Sign out could not be confirmed. Try again.");
      throw error;
    }
    clear();
    setNotice("You are signed out.");
  }
  return (
    <Auth.Provider
      value={{
        operator,
        hatchery,
        setHatchery,
        loading,
        notice,
        login,
        logout,
        clear,
        message,
      }}
    >
      {children}
    </Auth.Provider>
  );
}
