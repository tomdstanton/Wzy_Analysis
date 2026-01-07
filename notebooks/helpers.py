import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency, fisher_exact, kruskal, mannwhitneyu, false_discovery_control
import seaborn as sns
import matplotlib.pyplot as plt

class StatHelper:
    def __init__(self, df):
        self.df = df.copy()

    def _get_fdr(self, p_values):
        """Safe FDR correction handling NaNs"""
        p_clean = [p for p in p_values if not np.isnan(p)]
        if not p_clean: return p_values

        corrected = false_discovery_control(p_clean)
        result_map = dict(zip(np.where(~np.isnan(p_values))[0], corrected))

        return [result_map.get(i, np.nan) for i in range(len(p_values))]

    def run_omnibus_chi2(self, group_col, feature_col):
        """Global Chi2 test to see if any association exists."""
        cross_tab = pd.crosstab(self.df[feature_col], self.df[group_col])
        stat, p, dof, expected = chi2_contingency(cross_tab)
        return {"Test": "Chi2 Omnibus", "Feature": feature_col, "P-value": p, "Dof": dof}

    def run_pairwise_categorical(self, group_col, feature_col, mode='one_vs_one', min_obs=0):
        """
        Runs Fisher's Exact tests.
        mode='one_vs_one': Compares Group A vs Group B directly.
        mode='one_vs_rest': Compares Group A vs (All other Groups).
        """
        results = []

        # Filter for features with enough observations globally
        feature_counts = self.df[feature_col].value_counts()
        valid_features = feature_counts[feature_counts > min_obs].index

        if len(valid_features) == 0:
            print(f"No features in {feature_col} met the >{min_obs} observation threshold.")
            return pd.DataFrame()

        groups = self.df[group_col].unique()

        # --- STRATEGY 1: ONE VS ONE (e.g. WzyA vs WzyB) ---
        if mode == 'one_vs_one':
            import itertools
            for g1, g2 in itertools.combinations(groups, 2):
                # Subset data to just these two groups
                sub_df = self.df[self.df[group_col].isin([g1, g2])]

                for feat in valid_features:
                    # Create Contingency Table
                    #      | Feat | Not Feat
                    # ----------------------
                    # G1   |  a   |    b
                    # G2   |  c   |    d

                    a = ((sub_df[group_col] == g1) & (sub_df[feature_col] == feat)).sum()
                    b = ((sub_df[group_col] == g1) & (sub_df[feature_col] != feat)).sum()
                    c = ((sub_df[group_col] == g2) & (sub_df[feature_col] == feat)).sum()
                    d = ((sub_df[group_col] == g2) & (sub_df[feature_col] != feat)).sum()

                    odds, p = fisher_exact([[a, b], [c, d]])
                    results.append({
                        "Comparison": f"{g1} vs {g2}",
                        "Feature": feat,
                        "Count_G1": a,
                        "Count_G2": c,
                        "P_value": p
                    })

        # --- STRATEGY 2: ONE VS REST (e.g. WzyA vs Not-WzyA) ---
        elif mode == 'one_vs_rest':
            for group in groups:
                for feat in valid_features:
                    #      | Feat | Not Feat
                    # ----------------------
                    # Grp  |  a   |    b
                    # Rest |  c   |    d

                    a = ((self.df[group_col] == group) & (self.df[feature_col] == feat)).sum()
                    b = ((self.df[group_col] == group) & (self.df[feature_col] != feat)).sum()
                    c = ((self.df[group_col] != group) & (self.df[feature_col] == feat)).sum()
                    d = ((self.df[group_col] != group) & (self.df[feature_col] != feat)).sum()

                    odds, p = fisher_exact([[a, b], [c, d]])
                    results.append({
                        "Group": group,
                        "Feature": feat,
                        "In_Group_Count": a,
                        "Out_Group_Count": c,
                        "P_value": p
                    })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df['P_adj'] = self._get_fdr(res_df['P_value'].values)

            # Sort by significance
            res_df = res_df.sort_values('P_adj')
        return res_df

    def run_numerical_distributions(self, group_col, value_col):
        """Kruskal-Wallis followed by Mann-Whitney U if significant."""
        groups = self.df[group_col].unique()
        group_data = [self.df[self.df[group_col] == g][value_col].dropna().values for g in groups]

        # Omnibus
        stat, p_kruskal = kruskal(*group_data)
        omnibus_res = {"Test": "Kruskal-Wallis", "Statistic": stat, "P-value": p_kruskal}

        pairwise_res = []
        if p_kruskal < 0.05:
            import itertools
            for g1, g2 in itertools.combinations(groups, 2):
                d1 = self.df[self.df[group_col] == g1][value_col].dropna()
                d2 = self.df[self.df[group_col] == g2][value_col].dropna()

                # Using Mann-Whitney U (Independent samples)
                stat, p = mannwhitneyu(d1, d2)
                pairwise_res.append({
                    "Comparison": f"{g1} vs {g2}",
                    "Median_1": d1.median(),
                    "Median_2": d2.median(),
                    "P_value": p
                })

            pw_df = pd.DataFrame(pairwise_res)
            pw_df['P_adj'] = self._get_fdr(pw_df['P_value'].values)
        else:
            pw_df = pd.DataFrame()

        return omnibus_res, pw_df

    def plot_distributions(self, group_col, value_col):
        """Visualisation helper"""
        plt.figure(figsize=(8, 5))
        sns.boxplot(data=self.df, x=group_col, y=value_col, hue=group_col, palette="Set2")
        sns.stripplot(data=self.df, x=group_col, y=value_col, color='black', alpha=0.3)
        plt.title(f"Distribution of {value_col} by {group_col}")
        # plt.tight_layout()
        plt.show()

    def plot_categorical_association(self, group_col, feature_col, normalize=True):
        """Visualisation helper for categorical associations (Stacked Bar)."""
        cross_tab = pd.crosstab(self.df[group_col], self.df[feature_col])
        if normalize:
            cross_tab = cross_tab.div(cross_tab.sum(axis=1), axis=0)
        cross_tab.plot(kind='bar', stacked=True, figsize=(8, 5), colormap="Set2")
        plt.title(f"{'Proportional ' if normalize else ''}Distribution of {feature_col} by {group_col}")
        plt.ylabel("Proportion" if normalize else "Count")
        plt.legend(title=feature_col, bbox_to_anchor=(1.05, 1), loc='upper left')
        # plt.tight_layout()
        plt.show()




