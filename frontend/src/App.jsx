import { useEffect, useMemo, useState } from "react";

import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Car,
  CheckCircle2,
  Cloud,
  Gauge,
  LayoutDashboard,
  Menu,
  Thermometer,
  TrendingUp,
  Wind,
  Zap,
} from "lucide-react";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import "./App.css";


const API_BASE = "http://127.0.0.1:5000";


function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [backendConnected, setBackendConnected] = useState(false);

  const [energyHistory, setEnergyHistory] = useState([]);
  const [airData, setAirData] = useState(null);
  const [trafficData, setTrafficData] = useState(null);
  const [weatherData, setWeatherData] = useState(null);

  const [loading, setLoading] = useState(true);

  const [predictionForm, setPredictionForm] = useState({
    voltage: "",
    current: "",
    power_factor: "",
  });

  const [anomalyForm, setAnomalyForm] = useState({
    energy_usage: "",
    power_factor: "",
    voltage: "",
    current: "",
  });

  const [predictionResult, setPredictionResult] = useState(null);
  const [anomalyResult, setAnomalyResult] = useState(null);

  const [predictionLoading, setPredictionLoading] = useState(false);
  const [anomalyLoading, setAnomalyLoading] = useState(false);


  // ==========================================================
  // FETCH ALL DATA
  // ==========================================================

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      const [
        healthResponse,
        energyResponse,
        airResponse,
        trafficResponse,
        weatherResponse,
      ] = await Promise.all([
        fetch(`${API_BASE}/`),
        fetch(`${API_BASE}/api/energy/history`),
        fetch(`${API_BASE}/api/air-quality`),
        fetch(`${API_BASE}/api/traffic`),
        fetch(`${API_BASE}/api/weather`),
      ]);

      if (healthResponse.ok) {
        setBackendConnected(true);
      } else {
        setBackendConnected(false);
      }

      if (energyResponse.ok) {
        const data = await energyResponse.json();
        setEnergyHistory(data.records || []);
      }

      if (airResponse.ok) {
        setAirData(await airResponse.json());
      }

      if (trafficResponse.ok) {
        setTrafficData(await trafficResponse.json());
      }

      if (weatherResponse.ok) {
        setWeatherData(await weatherResponse.json());
      }

    } catch (error) {
      console.error("Dashboard data loading failed:", error);
      setBackendConnected(false);
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadDashboardData();
  }, []);


  // ==========================================================
  // ENERGY PREDICTION
  // ==========================================================

  const handlePrediction = async (event) => {
    event.preventDefault();

    try {
      setPredictionLoading(true);
      setPredictionResult(null);

      const response = await fetch(
        `${API_BASE}/api/energy/predict`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            voltage: Number(predictionForm.voltage),
            current: Number(predictionForm.current),
            power_factor: Number(predictionForm.power_factor),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Prediction failed");
      }

      setPredictionResult(data);

      await loadDashboardData();

    } catch (error) {
      setPredictionResult({
        status: "error",
        error: error.message,
      });
    } finally {
      setPredictionLoading(false);
    }
  };


  // ==========================================================
  // ANOMALY DETECTION
  // ==========================================================

  const handleAnomalyDetection = async (event) => {
    event.preventDefault();

    try {
      setAnomalyLoading(true);
      setAnomalyResult(null);

      const response = await fetch(
        `${API_BASE}/api/energy/anomaly`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            energy_usage: Number(anomalyForm.energy_usage),
            power_factor: Number(anomalyForm.power_factor),
            voltage: Number(anomalyForm.voltage),
            current: Number(anomalyForm.current),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Anomaly detection failed"
        );
      }

      setAnomalyResult(data);

      await loadDashboardData();

    } catch (error) {
      setAnomalyResult({
        status: "error",
        error: error.message,
      });
    } finally {
      setAnomalyLoading(false);
    }
  };


  // ==========================================================
  // DASHBOARD STATISTICS
  // ==========================================================

  const anomalyCount = useMemo(() => {
    return energyHistory.filter(
      (item) => Number(item.is_anomaly) === 1
    ).length;
  }, [energyHistory]);


  const predictionCount = useMemo(() => {
    return energyHistory.filter(
      (item) =>
        item.predicted_energy !== null &&
        item.predicted_energy !== undefined
    ).length;
  }, [energyHistory]);


  const averageEnergy = useMemo(() => {
    const values = energyHistory
      .map((item) => Number(item.predicted_energy))
      .filter((value) => !Number.isNaN(value));

    if (!values.length) return 0;

    return (
      values.reduce((sum, value) => sum + value, 0) /
      values.length
    ).toFixed(1);
  }, [energyHistory]);


  // ==========================================================
  // ENERGY CHART DATA
  // ==========================================================

  const energyChartData = useMemo(() => {
    return [...energyHistory]
      .reverse()
      .map((item, index) => ({
        name: `R${index + 1}`,

        predicted:
          item.predicted_energy !== null &&
          item.predicted_energy !== undefined
            ? Number(item.predicted_energy)
            : null,

        actual:
          item.energy_usage !== null &&
          item.energy_usage !== undefined
            ? Number(item.energy_usage)
            : null,

        anomaly: Number(item.is_anomaly) === 1,
      }));
  }, [energyHistory]);


  // ==========================================================
  // AIR QUALITY CHART DATA
  // ==========================================================

  const airChartData = useMemo(() => {
    if (!airData?.records) return [];

    return airData.records.map((item, index) => ({
      name: `S${index + 1}`,

      pm25:
        item.pm25 !== null &&
        item.pm25 !== undefined
          ? Number(item.pm25)
          : null,

      co2:
        item.co2 !== null &&
        item.co2 !== undefined
          ? Number(item.co2)
          : null,
    }));
  }, [airData]);


  // ==========================================================
  // TRAFFIC CHART DATA
  // ==========================================================

  const trafficChartData = useMemo(() => {
    if (!trafficData?.records) return [];

    return trafficData.records.map((item, index) => ({
      name: `S${index + 1}`,

      traffic:
        item.traffic_count !== null &&
        item.traffic_count !== undefined
          ? Number(item.traffic_count)
          : null,
    }));
  }, [trafficData]);


  // ==========================================================
  // WEATHER CHART DATA
  // ==========================================================

  const weatherChartData = useMemo(() => {
    if (!weatherData?.records) return [];

    return weatherData.records.map((item, index) => ({
      name: `S${index + 1}`,

      temperature:
        item.temperature !== null &&
        item.temperature !== undefined
          ? Number(item.temperature)
          : null,

      humidity:
        item.humidity !== null &&
        item.humidity !== undefined
          ? Number(item.humidity)
          : null,
    }));
  }, [weatherData]);


  // ==========================================================
  // CITY INTELLIGENCE
  // ==========================================================

  const cityInsights = useMemo(() => {
    const insights = [];

    const pm25 = Number(
      airData?.summary?.averages?.pm25
    );

    const traffic = Number(
      trafficData?.summary?.averages?.traffic_count
    );

    const temperature = Number(
      weatherData?.summary?.averages?.temperature
    );


    // AIR QUALITY INSIGHT

    if (!Number.isNaN(pm25)) {

      if (pm25 > 100) {

        insights.push({
          type: "warning",
          title: "Air quality needs attention",
          message: `Average PM2.5 is ${pm25} μg/m³ in the collected readings.`,
        });

      } else if (pm25 > 60) {

        insights.push({
          type: "warning",
          title: "Elevated particulate levels",
          message: `Average PM2.5 is ${pm25} μg/m³ across the available readings.`,
        });

      } else {

        insights.push({
          type: "positive",
          title: "Air quality looks stable",
          message: `Average PM2.5 is ${pm25} μg/m³ in the current dataset.`,
        });

      }
    }


    // ENERGY ANOMALY INSIGHT

    if (anomalyCount > 0) {

      insights.push({
        type: "warning",
        title: "Potential energy anomalies detected",
        message: `${anomalyCount} stored reading${
          anomalyCount === 1 ? "" : "s"
        } have been flagged for review.`,
      });

    } else {

      insights.push({
        type: "positive",
        title: "No potential anomalies recorded",
        message:
          "No energy readings are currently flagged in the application history.",
      });

    }


    // TRAFFIC INSIGHT

    if (!Number.isNaN(traffic)) {

      insights.push({
        type: "info",
        title: "Traffic monitoring active",
        message: `Average traffic count is ${traffic} across the collected sensor readings.`,
      });

    }


    // WEATHER INSIGHT

    if (!Number.isNaN(temperature)) {

      insights.push({
        type: "info",
        title: "Weather conditions available",
        message: `Average recorded temperature is ${temperature}°C.`,
      });

    }


    return insights.slice(0, 4);

  }, [
    airData,
    trafficData,
    weatherData,
    anomalyCount,
  ]);


  // ==========================================================
  // NAVIGATION
  // ==========================================================

  const navigation = [
    {
      name: "Dashboard",
      icon: LayoutDashboard,
    },
    {
      name: "Energy Analytics",
      icon: Zap,
    },
    {
      name: "Air Quality",
      icon: Wind,
    },
    {
      name: "Traffic",
      icon: Car,
    },
    {
      name: "Weather",
      icon: Cloud,
    },
  ];


  return (
    <div className="app-shell">

      {/* ====================================================
          SIDEBAR
      ==================================================== */}

      <aside
        className={`sidebar ${
          sidebarOpen ? "open" : "closed"
        }`}
      >

        <div className="brand">

          <div className="brand-icon">
            <Activity size={22} />
          </div>

          {sidebarOpen && (
            <div>
              <h2>SmartCity</h2>
              <span>Urban Analytics</span>
            </div>
          )}

        </div>


        <nav className="navigation">

          <p className="nav-label">
            {sidebarOpen ? "MAIN MENU" : ""}
          </p>

          {navigation.map((item) => {

            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={`nav-item ${
                  activePage === item.name
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  setActivePage(item.name)
                }
                title={item.name}
              >

                <Icon size={19} />

                {sidebarOpen && (
                  <span>{item.name}</span>
                )}

              </button>
            );
          })}

        </nav>


        {sidebarOpen && (
          <div className="sidebar-bottom">

            <div className="system-card">

              <div className="system-icon">
                <Gauge size={18} />
              </div>

              <div>

                <strong>System Status</strong>

                <div className="system-status">

                  <span
                    className={
                      backendConnected
                        ? "status-dot online"
                        : "status-dot"
                    }
                  />

                  {backendConnected
                    ? "All systems operational"
                    : "Backend disconnected"}

                </div>

              </div>

            </div>

          </div>
        )}

      </aside>


      {/* ====================================================
          MAIN AREA
      ==================================================== */}

      <main className="main-content">

        {/* TOP BAR */}

        <header className="topbar">

          <button
            className="menu-button"
            onClick={() =>
              setSidebarOpen(!sidebarOpen)
            }
          >
            <Menu size={21} />
          </button>


          <div className="topbar-title">
            <span>Smart City Platform</span>
          </div>


          <div className="topbar-actions">

            <div className="connection-pill">

              <span
                className={
                  backendConnected
                    ? "status-dot online"
                    : "status-dot"
                }
              />

              {backendConnected
                ? "Connected"
                : "Offline"}

            </div>


            <button className="icon-button">
              <Bell size={19} />
            </button>


            <div className="avatar">
              SC
            </div>

          </div>

        </header>


        {/* PAGE CONTENT */}

        <section className="page-content">


          {/* =================================================
              DASHBOARD
          ================================================= */}

          {activePage === "Dashboard" && (

            <>

              {/* HERO */}

              <div className="hero-section">

                <div>

                  <div className="eyebrow">
                    SMART CITY MONITORING
                  </div>

                  <h1>
                    Urban Intelligence
                    <span> Dashboard</span>
                  </h1>

                  <p>
                    Monitor energy, air quality,
                    traffic and weather insights
                    from one platform.
                  </p>

                </div>


                <div className="hero-status">

                  <div className="hero-status-icon">
                    <Activity size={23} />
                  </div>

                  <div>

                    <small>
                      PLATFORM STATUS
                    </small>

                    <strong>
                      {backendConnected
                        ? "Operational"
                        : "Offline"}
                    </strong>

                  </div>

                </div>

              </div>


              {/* STAT CARDS */}

              <div className="stats-grid">

                <StatCard
                  icon={<Zap />}
                  title="Energy Predictions"
                  value={predictionCount}
                  subtitle="Model predictions"
                  trend="+ Active"
                  className="purple"
                />


                <StatCard
                  icon={<Wind />}
                  title="Air Quality"
                  value={
                    airData?.summary?.averages?.pm25 ??
                    "—"
                  }
                  subtitle="Avg PM2.5"
                  trend="μg/m³"
                  className="blue"
                />


                <StatCard
                  icon={<Car />}
                  title="Traffic"
                  value={
                    trafficData?.summary?.averages
                      ?.traffic_count ?? "—"
                  }
                  subtitle="Avg traffic count"
                  trend="vehicles"
                  className="orange"
                />


                <StatCard
                  icon={<AlertTriangle />}
                  title="Potential Anomalies"
                  value={anomalyCount}
                  subtitle="Flagged for review"
                  trend={
                    anomalyCount > 0
                      ? "Review"
                      : "Clear"
                  }
                  className="red"
                />

              </div>


              {/* ENERGY + WEATHER */}

              <div className="dashboard-grid">

                {/* ENERGY */}

                <div className="panel large-panel">

                  <PanelHeader
                    title="Energy Consumption"
                    subtitle="Prediction history"
                  />

                  <div className="chart-container">

                    {energyChartData.length > 0 ? (

                      <ResponsiveContainer
                        width="100%"
                        height="100%"
                      >

                        <AreaChart
                          data={energyChartData}
                        >

                          <defs>

                            <linearGradient
                              id="energyGradient"
                              x1="0"
                              y1="0"
                              x2="0"
                              y2="1"
                            >

                              <stop
                                offset="0%"
                                stopOpacity={0.35}
                              />

                              <stop
                                offset="100%"
                                stopOpacity={0}
                              />

                            </linearGradient>

                          </defs>


                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                          />


                          <XAxis
                            dataKey="name"
                            tickLine={false}
                            axisLine={false}
                          />


                          <YAxis
                            tickLine={false}
                            axisLine={false}
                          />


                          <Tooltip />


                          <Area
                            type="monotone"
                            dataKey="predicted"
                            strokeWidth={2}
                            fill="url(#energyGradient)"
                            name="Predicted"
                            connectNulls={false}
                          />


                          <Line
                            type="monotone"
                            dataKey="actual"
                            strokeWidth={2}
                            dot={false}
                            name="Actual"
                            connectNulls={false}
                          />

                        </AreaChart>

                      </ResponsiveContainer>

                    ) : (

                      <EmptyState
                        message="No energy records yet"
                      />

                    )}

                  </div>

                </div>


                {/* WEATHER */}

                <div className="panel">

                  <PanelHeader
                    title="Weather Snapshot"
                    subtitle="Sensor overview"
                  />


                  <div className="weather-main">

                    <div className="weather-icon">
                      <Cloud size={30} />
                    </div>


                    <div>

                      <span>
                        Average Temperature
                      </span>

                      <strong>
                        {weatherData?.summary?.averages
                          ?.temperature ?? "—"}
                        °C
                      </strong>

                    </div>

                  </div>


                  <div className="weather-details">

                    <div>

                      <Thermometer size={17} />

                      <span>
                        Humidity
                      </span>

                      <strong>
                        {weatherData?.summary?.averages
                          ?.humidity ?? "—"}%
                      </strong>

                    </div>


                    <div>

                      <Wind size={17} />

                      <span>
                        Wind
                      </span>

                      <strong>
                        {weatherData?.summary?.averages
                          ?.wind_speed ?? "—"}
                      </strong>

                    </div>

                  </div>

                </div>

              </div>


              {/* =================================================
                  CITY INTELLIGENCE
              ================================================= */}

              <div className="intelligence-section">

                <div className="section-heading">

                  <div>

                    <h2>
                      City Intelligence
                    </h2>

                    <p>
                      Automated observations generated
                      from the available sensor and
                      analytics data.
                    </p>

                  </div>

                </div>


                <div className="insights-grid">

                  {cityInsights.length > 0 ? (

                    cityInsights.map(
                      (insight, index) => (

                        <div
                          className={`insight-card ${insight.type}`}
                          key={`${insight.title}-${index}`}
                        >

                          <div className="insight-icon">

                            {insight.type ===
                            "warning" ? (

                              <AlertTriangle
                                size={19}
                              />

                            ) : insight.type ===
                              "positive" ? (

                              <CheckCircle2
                                size={19}
                              />

                            ) : (

                              <Activity
                                size={19}
                              />

                            )}

                          </div>


                          <div className="insight-content">

                            <strong>
                              {insight.title}
                            </strong>

                            <p>
                              {insight.message}
                            </p>

                          </div>

                        </div>

                      )
                    )

                  ) : (

                    <EmptyState
                      message="Waiting for sensor data..."
                    />

                  )}

                </div>

              </div>


              {/* =================================================
                  SENSOR OVERVIEW
              ================================================= */}

              <div className="section-heading">

                <div>

                  <h2>
                    Sensor Overview
                  </h2>

                  <p>
                    Current dataset coverage across
                    monitored city systems.
                  </p>

                </div>

              </div>


              <div className="sensor-grid">

                <SensorCard
                  icon={<Wind />}
                  title="Air Quality"
                  records={
                    airData?.summary?.total_records
                  }
                  missing={
                    airData?.summary?.missing_values
                  }
                  metric="PM2.5"
                  value={
                    airData?.summary?.averages?.pm25
                  }
                  onClick={() =>
                    setActivePage("Air Quality")
                  }
                />


                <SensorCard
                  icon={<Car />}
                  title="Traffic"
                  records={
                    trafficData?.summary?.total_records
                  }
                  missing={
                    trafficData?.summary?.missing_values
                  }
                  metric="Traffic"
                  value={
                    trafficData?.summary?.averages
                      ?.traffic_count
                  }
                  onClick={() =>
                    setActivePage("Traffic")
                  }
                />


                <SensorCard
                  icon={<Cloud />}
                  title="Weather"
                  records={
                    weatherData?.summary?.total_records
                  }
                  missing={
                    weatherData?.summary?.missing_values
                  }
                  metric="Temperature"
                  value={
                    weatherData?.summary?.averages
                      ?.temperature
                  }
                  onClick={() =>
                    setActivePage("Weather")
                  }
                />

              </div>

            </>

          )}


          {/* =================================================
              ENERGY ANALYTICS
          ================================================= */}

          {activePage === "Energy Analytics" && (

            <>

              <PageTitle
                eyebrow="ENERGY ANALYTICS"
                title="Energy Intelligence"
                description="Predict energy consumption and monitor potential anomalies using the trained ML models."
              />


              <div className="two-column-layout">

                {/* PREDICTION */}

                <div className="panel form-panel">

                  <PanelHeader
                    title="Energy Prediction"
                    subtitle="Enter sensor measurements"
                  />


                  <form
                    onSubmit={handlePrediction}
                    className="analytics-form"
                  >

                    <InputField
                      label="Voltage"
                      value={predictionForm.voltage}
                      onChange={(value) =>
                        setPredictionForm({
                          ...predictionForm,
                          voltage: value,
                        })
                      }
                      placeholder="e.g. 230"
                    />


                    <InputField
                      label="Current"
                      value={predictionForm.current}
                      onChange={(value) =>
                        setPredictionForm({
                          ...predictionForm,
                          current: value,
                        })
                      }
                      placeholder="e.g. 2.2"
                    />


                    <InputField
                      label="Power Factor"
                      value={
                        predictionForm.power_factor
                      }
                      onChange={(value) =>
                        setPredictionForm({
                          ...predictionForm,
                          power_factor: value,
                        })
                      }
                      placeholder="e.g. 0.95"
                    />


                    <button
                      className="primary-button"
                      disabled={predictionLoading}
                    >

                      <TrendingUp size={18} />

                      {predictionLoading
                        ? "Predicting..."
                        : "Predict Energy"}

                    </button>

                  </form>


                  {predictionResult && (

                    <ResultBox
                      success={
                        predictionResult.status ===
                        "success"
                      }
                      title={
                        predictionResult.status ===
                        "success"
                          ? "Prediction Complete"
                          : "Prediction Failed"
                      }
                      value={
                        predictionResult
                          .predicted_energy_usage
                      }
                      suffix="dataset units"
                      message={
                        predictionResult.error
                      }
                    />

                  )}

                </div>


                {/* ANOMALY */}

                <div className="panel form-panel">

                  <PanelHeader
                    title="Anomaly Detection"
                    subtitle="Check an energy reading"
                  />


                  <form
                    onSubmit={handleAnomalyDetection}
                    className="analytics-form"
                  >

                    <InputField
                      label="Energy Usage"
                      value={
                        anomalyForm.energy_usage
                      }
                      onChange={(value) =>
                        setAnomalyForm({
                          ...anomalyForm,
                          energy_usage: value,
                        })
                      }
                      placeholder="e.g. 500"
                    />


                    <InputField
                      label="Power Factor"
                      value={
                        anomalyForm.power_factor
                      }
                      onChange={(value) =>
                        setAnomalyForm({
                          ...anomalyForm,
                          power_factor: value,
                        })
                      }
                      placeholder="e.g. 0.95"
                    />


                    <InputField
                      label="Voltage"
                      value={anomalyForm.voltage}
                      onChange={(value) =>
                        setAnomalyForm({
                          ...anomalyForm,
                          voltage: value,
                        })
                      }
                      placeholder="e.g. 230"
                    />


                    <InputField
                      label="Current"
                      value={anomalyForm.current}
                      onChange={(value) =>
                        setAnomalyForm({
                          ...anomalyForm,
                          current: value,
                        })
                      }
                      placeholder="e.g. 2.2"
                    />


                    <button
                      className="secondary-button"
                      disabled={anomalyLoading}
                    >

                      <AlertTriangle size={18} />

                      {anomalyLoading
                        ? "Analyzing..."
                        : "Detect Anomaly"}

                    </button>

                  </form>


                  {anomalyResult && (

                    <ResultBox
                      success={
                        anomalyResult.status ===
                          "success" &&
                        !anomalyResult.anomaly
                      }
                      title={
                        anomalyResult.classification ||
                        "Detection Result"
                      }
                      message={
                        anomalyResult.error
                      }
                    />

                  )}

                </div>

              </div>


              {/* ENERGY CHART */}

              <div className="panel">

                <PanelHeader
                  title="Energy Prediction History"
                  subtitle="Records stored in SQLite"
                />


                <div className="chart-container large">

                  {energyChartData.length > 0 ? (

                    <ResponsiveContainer
                      width="100%"
                      height="100%"
                    >

                      <LineChart
                        data={energyChartData}
                      >

                        <CartesianGrid
                          strokeDasharray="3 3"
                          vertical={false}
                        />


                        <XAxis
                          dataKey="name"
                        />


                        <YAxis />


                        <Tooltip />


                        <Line
                          type="monotone"
                          dataKey="predicted"
                          strokeWidth={3}
                          dot
                          name="Predicted Energy"
                          connectNulls={false}
                        />


                        <Line
                          type="monotone"
                          dataKey="actual"
                          strokeWidth={2}
                          dot
                          name="Actual Energy"
                          connectNulls={false}
                        />

                      </LineChart>

                    </ResponsiveContainer>

                  ) : (

                    <EmptyState
                      message="No energy history available"
                    />

                  )}

                </div>

              </div>

            </>

          )}


          {/* =================================================
              AIR QUALITY
          ================================================= */}

          {activePage === "Air Quality" && (

            <>

              <PageTitle
                eyebrow="ENVIRONMENT"
                title="Air Quality Monitoring"
                description="Explore particulate matter, CO₂ and environmental sensor measurements."
              />


              <div className="stats-grid">

                <StatCard
                  icon={<Wind />}
                  title="Average PM2.5"
                  value={
                    airData?.summary?.averages?.pm25 ??
                    "—"
                  }
                  subtitle="Particulate matter"
                  trend="μg/m³"
                  className="blue"
                />


                <StatCard
                  icon={<Activity />}
                  title="Average CO₂"
                  value={
                    airData?.summary?.averages?.co2 ??
                    "—"
                  }
                  subtitle="Sensor average"
                  trend="ppm"
                  className="purple"
                />


                <StatCard
                  icon={<Gauge />}
                  title="Sensor Records"
                  value={
                    airData?.summary?.total_records ??
                    0
                  }
                  subtitle="Available readings"
                  trend="records"
                  className="orange"
                />


                <StatCard
                  icon={<AlertTriangle />}
                  title="Missing Values"
                  value={
                    airData?.summary?.missing_values ??
                    0
                  }
                  subtitle="Original dataset"
                  trend="values"
                  className="red"
                />

              </div>


              <div className="panel">

                <PanelHeader
                  title="PM2.5 & CO₂ Trends"
                  subtitle="Sensor readings"
                />


                <div className="chart-container large">

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >

                    <LineChart
                      data={airChartData}
                    >

                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                      />


                      <XAxis
                        dataKey="name"
                      />


                      <YAxis />


                      <Tooltip />


                      <Line
                        type="monotone"
                        dataKey="pm25"
                        strokeWidth={3}
                        dot={false}
                        name="PM2.5"
                      />


                      <Line
                        type="monotone"
                        dataKey="co2"
                        strokeWidth={2}
                        dot={false}
                        name="CO₂"
                      />

                    </LineChart>

                  </ResponsiveContainer>

                </div>

              </div>

            </>

          )}


          {/* =================================================
              TRAFFIC
          ================================================= */}

          {activePage === "Traffic" && (

            <>

              <PageTitle
                eyebrow="MOBILITY"
                title="Traffic Analytics"
                description="Monitor traffic sensor activity and identify changes across the collected readings."
              />


              <div className="stats-grid">

                <StatCard
                  icon={<Car />}
                  title="Average Traffic"
                  value={
                    trafficData?.summary?.averages
                      ?.traffic_count ?? "—"
                  }
                  subtitle="Sensor average"
                  trend="vehicles"
                  className="orange"
                />


                <StatCard
                  icon={<BarChart3 />}
                  title="Records"
                  value={
                    trafficData?.summary?.total_records ??
                    0
                  }
                  subtitle="Sensor readings"
                  trend="records"
                  className="blue"
                />


                <StatCard
                  icon={<AlertTriangle />}
                  title="Missing Values"
                  value={
                    trafficData?.summary?.missing_values ??
                    0
                  }
                  subtitle="Original dataset"
                  trend="values"
                  className="red"
                />

              </div>


              <div className="panel">

                <PanelHeader
                  title="Traffic Sensor Trend"
                  subtitle="Traffic count across readings"
                />


                <div className="chart-container large">

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >

                    <BarChart
                      data={trafficChartData}
                    >

                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                      />


                      <XAxis
                        dataKey="name"
                      />


                      <YAxis />


                      <Tooltip />


                      <Bar
                        dataKey="traffic"
                        name="Traffic Count"
                        radius={[5, 5, 0, 0]}
                      />

                    </BarChart>

                  </ResponsiveContainer>

                </div>

              </div>

            </>

          )}


          {/* =================================================
              WEATHER
          ================================================= */}

          {activePage === "Weather" && (

            <>

              <PageTitle
                eyebrow="ENVIRONMENT"
                title="Weather Analytics"
                description="Monitor temperature, humidity, wind and precipitation measurements."
              />


              <div className="stats-grid">

                <StatCard
                  icon={<Thermometer />}
                  title="Temperature"
                  value={
                    weatherData?.summary?.averages
                      ?.temperature ?? "—"
                  }
                  subtitle="Average"
                  trend="°C"
                  className="orange"
                />


                <StatCard
                  icon={<Cloud />}
                  title="Humidity"
                  value={
                    weatherData?.summary?.averages
                      ?.humidity ?? "—"
                  }
                  subtitle="Average"
                  trend="%"
                  className="blue"
                />


                <StatCard
                  icon={<Wind />}
                  title="Wind Speed"
                  value={
                    weatherData?.summary?.averages
                      ?.wind_speed ?? "—"
                  }
                  subtitle="Average"
                  trend="units"
                  className="purple"
                />


                <StatCard
                  icon={<Gauge />}
                  title="Records"
                  value={
                    weatherData?.summary?.total_records ??
                    0
                  }
                  subtitle="Sensor readings"
                  trend="records"
                  className="red"
                />

              </div>


              <div className="panel">

                <PanelHeader
                  title="Temperature & Humidity"
                  subtitle="Weather sensor readings"
                />


                <div className="chart-container large">

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >

                    <LineChart
                      data={weatherChartData}
                    >

                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                      />


                      <XAxis
                        dataKey="name"
                      />


                      <YAxis />


                      <Tooltip />


                      <Line
                        type="monotone"
                        dataKey="temperature"
                        strokeWidth={3}
                        dot={false}
                        name="Temperature"
                      />


                      <Line
                        type="monotone"
                        dataKey="humidity"
                        strokeWidth={2}
                        dot={false}
                        name="Humidity"
                      />

                    </LineChart>

                  </ResponsiveContainer>

                </div>

              </div>

            </>

          )}

        </section>

      </main>

    </div>
  );
}


// ============================================================
// REUSABLE COMPONENTS
// ============================================================

function StatCard({
  icon,
  title,
  value,
  subtitle,
  trend,
  className = "",
}) {

  return (

    <div className={`stat-card ${className}`}>

      <div className="stat-top">

        <div className="stat-icon">
          {icon}
        </div>

        <span className="stat-trend">
          {trend}
        </span>

      </div>


      <div className="stat-value">
        {value}
      </div>


      <div className="stat-title">
        {title}
      </div>


      <div className="stat-subtitle">
        {subtitle}
      </div>

    </div>
  );
}


function PanelHeader({
  title,
  subtitle,
}) {

  return (

    <div className="panel-header">

      <div>

        <h3>{title}</h3>

        <span>
          {subtitle}
        </span>

      </div>


      <div className="panel-indicator">
        <span />
      </div>

    </div>
  );
}


function PageTitle({
  eyebrow,
  title,
  description,
}) {

  return (

    <div className="page-title">

      <div className="eyebrow">
        {eyebrow}
      </div>

      <h1>
        {title}
      </h1>

      <p>
        {description}
      </p>

    </div>
  );
}


function InputField({
  label,
  value,
  onChange,
  placeholder,
}) {

  return (

    <div className="input-group">

      <label>
        {label}
      </label>

      <input
        type="number"
        step="any"
        value={value}
        placeholder={placeholder}
        onChange={(event) =>
          onChange(event.target.value)
        }
        required
      />

    </div>
  );
}


function ResultBox({
  success,
  title,
  value,
  suffix,
  message,
}) {

  return (

    <div
      className={`result-box ${
        success
          ? "success"
          : "warning"
      }`}
    >

      <div className="result-icon">

        {success ? (
          <CheckCircle2 />
        ) : (
          <AlertTriangle />
        )}

      </div>


      <div>

        <strong>
          {title}
        </strong>


        {value !== undefined &&
          value !== null && (

            <div className="result-value">

              {value}

              <small>
                {suffix}
              </small>

            </div>

          )}


        {message && (
          <p>
            {message}
          </p>
        )}

      </div>

    </div>
  );
}


function SensorCard({
  icon,
  title,
  records,
  missing,
  metric,
  value,
  onClick,
}) {

  return (

    <button
      className="sensor-card"
      onClick={onClick}
    >

      <div className="sensor-card-top">

        <div className="sensor-icon">
          {icon}
        </div>

        <span>
          View analytics →
        </span>

      </div>


      <h3>
        {title}
      </h3>


      <div className="sensor-value">
        {value ?? "—"}
      </div>


      <div className="sensor-metric">
        {metric}
      </div>


      <div className="sensor-footer">

        <span>
          {records ?? 0} records
        </span>

        <span>
          {missing ?? 0} missing
        </span>

      </div>

    </button>
  );
}


function EmptyState({
  message,
}) {

  return (

    <div className="empty-state">

      <Activity size={30} />

      <span>
        {message}
      </span>

    </div>
  );
}


export default App;