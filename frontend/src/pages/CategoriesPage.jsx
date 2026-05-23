import { Plus } from "lucide-react";
import { useEffect, useState } from "react";

import { budgetApi } from "../api/client";
import { CategoryCard } from "../components/CategoryCard";
import { CategoryFormModal } from "../components/CategoryFormModal";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { SectionCard } from "../components/SectionCard";
import { StatCard } from "../components/StatCard";
import { useToast } from "../components/ToastProvider";
import { formatCurrency } from "../utils/format";

export function CategoriesPage() {
  const toast = useToast();
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingCategory, setEditingCategory] = useState(null);
  const [showModal, setShowModal] = useState(false);

  async function loadCategories() {
    try {
      const response = await budgetApi.getCategories();
      setCategories(response);
    } catch (error) {
      toast.error("Unable to load categories", error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCategories();
  }, []);

  async function handleSubmit(payload) {
    try {
      if (editingCategory) {
        await budgetApi.updateCategory(editingCategory.id, payload);
        toast.success("Category updated", "Your changes are saved.");
      } else {
        await budgetApi.createCategory(payload);
        toast.success("Category added", "Your new envelope is ready to go.");
      }
      setShowModal(false);
      setEditingCategory(null);
      await loadCategories();
    } catch (error) {
      toast.error("Could not save category", error.message);
    }
  }

  async function handleDelete(category) {
    const confirmed = window.confirm(
      `Delete "${category.name}"? Categories must have a zero balance before they can be removed.`
    );
    if (!confirmed) {
      return;
    }

    try {
      await budgetApi.deleteCategory(category.id);
      toast.success("Category removed", "It's no longer in your plan.");
      await loadCategories();
    } catch (error) {
      toast.error("Could not delete category", error.message);
    }
  }

  if (loading) {
    return <LoadingState message="Loading your categories..." />;
  }

  const totalBalance = categories.reduce((sum, category) => sum + Number(category.balance), 0);
  const totalTarget = categories.reduce((sum, category) => sum + Number(category.monthly_budget), 0);

  return (
    <div className="page-stack">
      <section className="hero-banner">
        <div>
          <span className="eyebrow">Your envelopes</span>
          <h2>Plan the envelopes that hold your money</h2>
          <p>
            Give each part of your budget a name, a color, and a monthly target — make it
            yours.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => {
            setEditingCategory(null);
            setShowModal(true);
          }}
        >
          <Plus size={16} />
          Add category
        </button>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Categories"
          value={categories.length}
          accent="neutral"
          meta="Envelopes in your plan"
        />
        <StatCard
          label="Allocated balance"
          value={formatCurrency(totalBalance)}
          accent="success"
          meta="Money tucked into your envelopes"
        />
        <StatCard
          label="Monthly targets"
          value={formatCurrency(totalTarget)}
          accent="warning"
          meta="Combined target across categories"
        />
      </section>

      <SectionCard
        title="All categories"
        subtitle="Tweak names, colors, icons, and monthly targets any time"
      >
        {categories.length ? (
          <div className="category-grid category-grid--full">
            {categories.map((category) => (
              <CategoryCard
                key={category.id}
                category={category}
                onEdit={(selectedCategory) => {
                  setEditingCategory(selectedCategory);
                  setShowModal(true);
                }}
                onDelete={handleDelete}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            eyebrow="No categories yet"
            title="Add your first category"
            description="Try starting with food, rent, or savings — you can always change them later."
            action={
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setEditingCategory(null);
                  setShowModal(true);
                }}
              >
                <Plus size={16} />
                Create category
              </button>
            }
          />
        )}
      </SectionCard>

      {showModal ? (
        <CategoryFormModal
          category={editingCategory}
          onClose={() => {
            setShowModal(false);
            setEditingCategory(null);
          }}
          onSubmit={handleSubmit}
        />
      ) : null}
    </div>
  );
}
