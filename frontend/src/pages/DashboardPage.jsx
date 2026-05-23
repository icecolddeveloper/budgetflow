import { ArrowRightLeft, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { budgetApi } from "../api/client";
import { CashflowChart } from "../components/CashflowChart";
import { CategoryCard } from "../components/CategoryCard";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { SectionCard } from "../components/SectionCard";
import { SpendingChart } from "../components/SpendingChart";
import { StatCard } from "../components/StatCard";
import { useToast } from "../components/ToastProvider";
import { TransactionFormModal } from "../components/TransactionFormModal";
import { TransactionsList } from "../components/TransactionsList";
import { UnverifiedBanner } from "../components/UnverifiedBanner";
import { WelcomeModal } from "../components/WelcomeModal";
import { useAuth } from "../context/AuthContext";
import { formatCurrency } from "../utils/format";

const WELCOME_STORAGE_PREFIX = "budgetflow.welcome_seen.";

export function DashboardPage() {
  const toast = useToast();
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTransactionModal, setShowTransactionModal] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);

  async function loadDashboard() {
    try {
      const response = await budgetApi.getDashboard();
      setDashboard(response);
    } catch (error) {
      toast.error("Unable to load dashboard", error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    if (!user?.id) {
      return;
    }
    const key = `${WELCOME_STORAGE_PREFIX}${user.id}`;
    if (!window.localStorage.getItem(key)) {
      setShowWelcome(true);
    }
  }, [user?.id]);

  function dismissWelcome() {
    if (user?.id) {
      window.localStorage.setItem(`${WELCOME_STORAGE_PREFIX}${user.id}`, "1");
    }
    setShowWelcome(false);
  }

  async function handleTransactionCreate(payload) {
    try {
      await budgetApi.createTransaction(payload);
      toast.success("Transaction saved", "Your balances and charts are up to date.");
      setShowTransactionModal(false);
      await loadDashboard();
    } catch (error) {
      toast.error("Could not save transaction", error.message);
      throw error;
    }
  }

  if (loading) {
    return <LoadingState message="Loading your dashboard..." />;
  }

  if (!dashboard) {
    return (
      <EmptyState
        eyebrow="Dashboard unavailable"
        title="We couldn't load your dashboard"
        description="Try refreshing once the backend is back up."
      />
    );
  }

  const topCategories = dashboard.categories.slice(0, 4);
  const trendData = dashboard.cashflow_trend.map((item) => ({
    ...item,
    deposits: Number(item.deposits),
    spending: Number(item.spending),
  }));
  const spendingData = dashboard.spending_breakdown.map((item) => ({
    ...item,
    total: Number(item.total),
  }));

  return (
    <div className="page-stack">
      {user && user.email_verified === false ? (
        <UnverifiedBanner email={user.email} />
      ) : null}
      <section className="hero-banner">
        <div>
          <span className="eyebrow">This month</span>
          <h2>{formatCurrency(dashboard.total_balance)} ready to use across your envelopes</h2>
          <p>
            Take a look at how your categories are doing, what's moved lately, and where your
            money is flowing.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setShowTransactionModal(true)}>
          <ArrowRightLeft size={16} />
          New transaction
        </button>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Total balance"
          value={formatCurrency(dashboard.total_balance)}
          accent="success"
          meta="Available across all categories"
        />
        <StatCard
          label="Monthly inflow"
          value={formatCurrency(dashboard.monthly_inflow)}
          accent="success"
          meta="Funds added this month"
        />
        <StatCard
          label="Monthly outflow"
          value={formatCurrency(dashboard.monthly_outflow)}
          accent="warning"
          meta="Spending and transfers out"
        />
        <StatCard
          label="Active categories"
          value={dashboard.category_count}
          accent="neutral"
          meta="Envelopes you're tracking"
        />
      </section>

      <section className="dashboard-grid">
        <SectionCard
          title="Spending trend"
          subtitle="Six-month view of deposits versus outflow"
          className="dashboard-grid__wide"
        >
          <CashflowChart data={trendData} />
        </SectionCard>

        <SectionCard title="Spending mix" subtitle="Where most of your spending is going">
          {spendingData.length ? (
            <>
              <SpendingChart data={spendingData} />
              <div className="legend-list">
                {spendingData.map((item) => (
                  <div key={item.category} className="legend-item">
                    <span className="legend-item__swatch" style={{ backgroundColor: item.color }} />
                    <div>
                      <strong>{item.category}</strong>
                      <p>{formatCurrency(item.total)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <EmptyState
              eyebrow="No outflow yet"
              title="Your chart is waiting for some action"
              description="Log an expense or transfer to start seeing where your money goes."
              action={
                <button type="button" className="btn btn-secondary" onClick={() => setShowTransactionModal(true)}>
                  <Plus size={16} />
                  Add first transaction
                </button>
              }
            />
          )}
        </SectionCard>
      </section>

      <section className="dashboard-grid">
        <SectionCard
          title="Category balances"
          subtitle="Your top funded categories at a glance"
          action={
            <Link to="/categories" className="text-link">
              Manage categories
            </Link>
          }
          className="dashboard-grid__wide"
        >
          {topCategories.length ? (
            <div className="category-grid">
              {topCategories.map((category) => (
                <CategoryCard key={category.id} category={category} compact />
              ))}
            </div>
          ) : (
            <EmptyState
              eyebrow="No categories"
              title="Let's start your budget"
              description="Create your first category and decide where money should go."
            />
          )}
        </SectionCard>

        <SectionCard title="Recent activity" subtitle="Your latest money moves">
          {dashboard.recent_transactions.length ? (
            <TransactionsList transactions={dashboard.recent_transactions} compact />
          ) : (
            <EmptyState
              eyebrow="No activity yet"
              title="You're all set"
              description="Your transactions will show up here as soon as you add one."
            />
          )}
        </SectionCard>
      </section>

      {showTransactionModal ? (
        <TransactionFormModal
          categories={dashboard.categories}
          onClose={() => setShowTransactionModal(false)}
          onSubmit={handleTransactionCreate}
        />
      ) : null}

      {showWelcome ? <WelcomeModal onClose={dismissWelcome} /> : null}
    </div>
  );
}
