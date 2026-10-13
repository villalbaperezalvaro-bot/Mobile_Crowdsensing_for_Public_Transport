package com.pruebas_inaoe.sensadomovil;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.Filter;
import android.widget.Filterable;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;

public class CampaignAdapter extends RecyclerView.Adapter<CampaignAdapter.CampaignViewHolder> implements Filterable {

    private List<Campaign> campaignList;
    private List<Campaign> campaignListFull;
    private OnCampaignClickListener listener;

    public interface OnCampaignClickListener {
        void onParticiparClick(Campaign campaign);
    }

    public CampaignAdapter(List<Campaign> campaignList, OnCampaignClickListener listener) {
        this.campaignList = campaignList;
        this.campaignListFull = new ArrayList<>(campaignList);
        this.listener = listener;
    }

    @NonNull
    @Override
    public CampaignViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_campaign_card, parent, false);
        return new CampaignViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull CampaignViewHolder holder, int position) {
        Campaign campaign = campaignList.get(position);
        holder.tvName.setText(campaign.name);
        holder.tvDescription.setText(campaign.description);

        holder.btnParticipar.setOnClickListener(v -> {
            if (listener != null) {
                listener.onParticiparClick(campaign);
            }
        });
    }

    @Override
    public int getItemCount() {
        return campaignList.size();
    }

    @Override
    public Filter getFilter() {
        return campaignFilter;
    }

    private Filter campaignFilter = new Filter() {
        @Override
        protected FilterResults performFiltering(CharSequence constraint) {
            List<Campaign> filteredList = new ArrayList<>();

            if (constraint == null || constraint.length() == 0) {
                filteredList.addAll(campaignListFull);
            } else {
                String filterPattern = constraint.toString().toLowerCase().trim();

                for (Campaign item : campaignListFull) {
                    if (item.name.toLowerCase().contains(filterPattern) || 
                        (item.description != null && item.description.toLowerCase().contains(filterPattern))) {
                        filteredList.add(item);
                    }
                }
            }

            FilterResults results = new FilterResults();
            results.values = filteredList;
            return results;
        }

        @Override
        protected void publishResults(CharSequence constraint, FilterResults results) {
            campaignList.clear();
            campaignList.addAll((List) results.values);
            notifyDataSetChanged();
        }
    };

    public void updateList(List<Campaign> newList) {
        this.campaignListFull = new ArrayList<>(newList);
        this.campaignList.clear();
        this.campaignList.addAll(newList);
        notifyDataSetChanged();
    }

    static class CampaignViewHolder extends RecyclerView.ViewHolder {
        TextView tvName, tvDescription;
        Button btnParticipar;

        public CampaignViewHolder(@NonNull View itemView) {
            super(itemView);
            tvName = itemView.findViewById(R.id.tvCampaignName);
            tvDescription = itemView.findViewById(R.id.tvCampaignDescription);
            btnParticipar = itemView.findViewById(R.id.btnParticipar);
        }
    }
}
