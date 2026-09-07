import { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

type SystemInfo = {
  status: string;
  hostname: string;
  cpu_percent: number;
  temperature: number | null;
  memory: {
    total_gb: number;
    used_gb: number;
    percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  ssd: {
    mounted: boolean;
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  uptime_seconds: number;
};

type ServiceItem = {
  name: string;
  status: string;
  running: boolean;
  port?: number;
};

type Services = {
  systemd: ServiceItem[];
  apps: ServiceItem[];
  docker: ServiceItem[];
};

type ProcessInfo = {
  pid: number;
  name: string;
  cpu: number;
  memory: number;
};

function formatUptime(seconds: number) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  return `${days} d. ${hours} val. ${minutes} min.`;
}

function getLevel(value: number) {
  if (value >= 85) return "danger";
  if (value >= 70) return "warning";
  return "good";
}

function getTemperatureLevel(value: number | null) {
  if (value === null) return "neutral";
  if (value >= 80) return "danger";
  if (value >= 70) return "warning";
  return "good";
}

function MetricCard({
  title,
  value,
  subtitle,
  percent,
  level = "good",
}: {
  title: string;
  value: string;
  subtitle?: string;
  percent?: number;
  level?: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-title">{title}</div>

      <div className={`metric-value ${level}`}>
        {value}
      </div>

      {subtitle && (
        <div className="metric-subtitle">
          {subtitle}
        </div>
      )}

      {percent !== undefined && (
        <div className="progress-track">
          <div
            className={`progress-fill ${level}`}
            style={{
              width: `${Math.min(percent, 100)}%`,
            }}
          />
        </div>
      )}
    </div>
  );
}

function ServiceRow({
  service,
  onAction,
}: {
  service: ServiceItem;
  onAction?: (
    name: string,
    action: "start" | "stop" | "restart"
  ) => void;
}) {
  return (
    <div className="service-row">
      <div>
        <div className="service-name">
          {service.name}
        </div>

        {service.port && (
          <div className="service-port">
            Portas {service.port}
          </div>
        )}
      </div>

      <div className="service-actions">
        <div
          className={`service-status ${service.running ? "online" : "offline"
            }`}
        >
          <span className="status-dot" />
          {service.running ? "Veikia" : "Neveikia"}
        </div>

        {onAction && (
          <>
            {service.running ? (
              <>
                <button
                  className="btn icon-btn secondary"
                  title="Perkrauti"
                  aria-label="Perkrauti"
                  onClick={() =>
                    onAction(service.name, "restart")
                  }
                >
                  ↻
                </button>

                <button
                  className="btn icon-btn danger"
                  title="Sustabdyti"
                  aria-label="Sustabdyti"
                  onClick={() => {
                    const confirmed = window.confirm(
                      `Tikrai sustabdyti „${service.name}“?`
                    );

                    if (confirmed) {
                      onAction(service.name, "stop");
                    }
                  }}
                >
                  ■
                </button>
              </>
            ) : (
              <button
                className="btn icon-btn success"
                title="Paleisti"
                aria-label="Paleisti"
                onClick={() =>
                  onAction(service.name, "start")
                }
              >
                ▶
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function App() {
  const [processes, setProcesses] = useState<ProcessInfo[]>([]);

  const [system, setSystem] =
    useState<SystemInfo | null>(null);

  const [services, setServices] =
    useState<Services | null>(null);

  const [error, setError] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [systemRes, servicesRes] =
          await Promise.all([
            axios.get(
              "/api/system"
            ),
            axios.get(
              "/api/services"
            ),
          ]);

        setSystem(systemRes.data);
        setServices(servicesRes.data);
        setError(false);
      } catch (err) {
        console.error(err);
        setError(true);
      }

      const [systemRes, servicesRes, processesRes] =
        await Promise.all([
          axios.get(
            "/api/system"
          ),
          axios.get(
            "/api/services"
          ),
          axios.get(
            "/api/processes"
          ),
        ]);

      setSystem(systemRes.data);
      setServices(servicesRes.data);
      setProcesses(processesRes.data);
    };

    loadData();

    const interval = setInterval(
      loadData,
      5000
    );

    return () => clearInterval(interval);
  }, []);

  if (!system || !services) {
    return (
      <div className="loading-screen">
        {error
          ? "Nepavyksta prisijungti prie Raspberry Pi"
          : "Kraunami serverio duomenys..."}
      </div>
    );
  }

  const controlSystemd = async (
    service: string,
    action: "start" | "stop" | "restart"
  ) => {
    await axios.post(
      `/api/services/systemd/${service}/${action}`
    );
  };

  const controlDocker = async (
    container: string,
    action: "start" | "stop" | "restart"
  ) => {
    await axios.post(
      `/api/services/docker/${container}/${action}`
    );
  };

  const shutdownPi = async () => {
    const confirmed = window.confirm(
      "Tikrai išjungti Raspberry Pi? Po išjungimo palauk, kol Pi pilnai sustos, ir tik tada atjunk maitinimą."
    );

    if (!confirmed) return;

    await axios.post(
      "/api/system/shutdown"
    );
  };

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="eyebrow">
            SERVERIO VALDYMAS
          </div>

          <h1>Raspberry Monitor</h1>

          <div className="hostname">
            {system.hostname}
          </div>
        </div>

        <div className="online-badge">
          <span className="status-dot" />
          Online
        </div>
      </header>

      <main>
        <section>
          <div className="section-header">
            <div>
              <h2>Sistema</h2>
              <p>
                Raspberry Pi būklė realiu laiku
              </p>
            </div>

            <div className="refresh-text">
              Atnaujinama kas 5 s
            </div>
          </div>

          <div className="metrics-grid">
            <MetricCard
              title="CPU"
              value={`${system.cpu_percent}%`}
              percent={system.cpu_percent}
              level={getLevel(
                system.cpu_percent
              )}
              subtitle="Procesoriaus apkrova"
            />

            <MetricCard
              title="Temperatūra"
              value={
                system.temperature !== null
                  ? `${system.temperature} °C`
                  : "N/A"
              }
              percent={
                system.temperature ?? 0
              }
              level={getTemperatureLevel(
                system.temperature
              )}
              subtitle="CPU temperatūra"
            />

            <MetricCard
              title="RAM"
              value={`${system.memory.percent}%`}
              percent={
                system.memory.percent
              }
              level={getLevel(
                system.memory.percent
              )}
              subtitle={`${system.memory.used_gb} / ${system.memory.total_gb} GB`}
            />

            <MetricCard
              title="SD kortelė"
              value={`${system.disk.percent}%`}
              percent={
                system.disk.percent
              }
              level={getLevel(
                system.disk.percent
              )}
              subtitle={`${system.disk.used_gb} / ${system.disk.total_gb} GB`}
            />

            <MetricCard
              title="SSD"
              value={
                system.ssd.mounted
                  ? `${system.ssd.percent}%`
                  : "Neprijungtas"
              }
              percent={
                system.ssd.mounted
                  ? system.ssd.percent
                  : 0
              }
              level={
                system.ssd.mounted
                  ? getLevel(
                    system.ssd.percent
                  )
                  : "danger"
              }
              subtitle={
                system.ssd.mounted
                  ? `${system.ssd.used_gb} / ${system.ssd.total_gb} GB`
                  : "Diskas nematomas"
              }
            />

            <MetricCard
              title="Veikimo laikas"
              value={formatUptime(
                system.uptime_seconds
              )}
              subtitle="Nuo paskutinio paleidimo"
            />
          </div>
        </section>

        <section className="services-section">
          <div className="section-header">
            <div>
              <h2>Programos</h2>
              <p>
                Tavo Raspberry Pi servisai
              </p>
            </div>
          </div>

          <div className="service-panel">
            {services.apps.map((service) => (
              <ServiceRow
                key={service.name}
                service={service}
              />
            ))}

            {services.systemd.map((service) => (
              <ServiceRow
                key={service.name}
                service={service}
                onAction={(name, action) =>
                  controlSystemd(
                    name.replace(".service", ""),
                    action
                  )
                }
              />
            ))}
          </div>
        </section>

        <section className="services-section">
          <div className="section-header">
            <div>
              <h2>Immich</h2>
              <p>
                Docker konteinerių būsena
              </p>
            </div>
          </div>

          <div className="service-panel">
            {services.docker.map((service) => (
              <ServiceRow
                key={service.name}
                service={service}
                onAction={controlDocker}
              />
            ))}
          </div>
        </section>

        <section className="services-section">
          <div className="section-header">
            <div>
              <h2>CPU procesai</h2>
              <p>Didžiausi procesoriaus naudotojai</p>
            </div>
          </div>

          <div className="process-panel">
            {processes.slice(0, 6).map((process) => (
              <div className="process-row" key={process.pid}>
                <div>
                  <div className="process-name">
                    {process.name}
                  </div>

                  <div className="process-pid">
                    PID {process.pid}
                  </div>
                </div>

                <div className="process-values">
                  <strong>{process.cpu}% CPU</strong>
                  <span>{process.memory}% RAM</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="danger-zone">
          <h2>Raspberry Pi valdymas</h2>

          <button
            className="shutdown-button"
            onClick={shutdownPi}
          >
            ⏻ Išjungti Raspberry Pi
          </button>
        </section>
      </main>
    </div>
  );
}

export default App;