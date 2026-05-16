import { useState, useEffect } from 'react';
import { Check, X, Clock, AlertCircle, Loader2, Brain, Ticket, MessageSquare } from 'lucide-react';
import { fetchPendingProposals, approveProposal, rejectProposal } from '../services/apiService';
import ToastProvider, { showSuccessToast, showErrorToast } from '../components/Toast';

const PendingProposalsPage = () => {
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rejectModal, setRejectModal] = useState(null);
  const [rejectForm, setRejectForm] = useState({ rejection_reason: '', reviewer_id: '' });

  // Fetch pending proposals from the API on component mount
  useEffect(() => {
    loadProposals();
  }, []);

  const loadProposals = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchPendingProposals();
      setProposals(data);
    } catch (err) {
      setError('Failed to load proposals. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (proposalId) => {
    try {
      await approveProposal(proposalId);
      // Remove approved proposal from the list
      setProposals(proposals.filter(p => p.id !== proposalId));
      showSuccessToast('Proposal approved successfully! Action executed.');
    } catch (err) {
      showErrorToast('Error approving proposal: ' + err.message);
    }
  };

  const openRejectModal = (proposalId) => {
    setRejectModal(proposalId);
    // Pre-fill with hardcoded reviewer_id
    setRejectForm({ rejection_reason: '', reviewer_id: 'founder_01' });
  };

  const handleReject = async (e) => {
    e.preventDefault();
    try {
      await rejectProposal(rejectModal, rejectForm.rejection_reason, rejectForm.reviewer_id);
      // Remove rejected proposal from the list
      setProposals(proposals.filter(p => p.id !== rejectModal));
      setRejectModal(null);
      setRejectForm({ rejection_reason: '', reviewer_id: '' });
      showSuccessToast('Proposal rejected. Feedback logged for ML training.');
    } catch (err) {
      showErrorToast('Error rejecting proposal: ' + err.message);
    }
  };

  const getActionColor = (action) => {
    const colors = {
      'escalate_urgent': 'bg-red-100 text-red-700 border-red-200',
      'route_to_senior': 'bg-orange-100 text-orange-700 border-orange-200',
      'send_kb_article': 'bg-blue-100 text-blue-700 border-blue-200',
      'request_more_info': 'bg-yellow-100 text-yellow-700 border-yellow-200',
      'auto_respond': 'bg-green-100 text-green-700 border-green-200',
    };
    return colors[action] || 'bg-slate-100 text-slate-700 border-slate-200';
  };

  const formatActionName = (action) => {
    return action.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-slate-600">Failed to load proposals</p>
          <p className="text-sm text-slate-500">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800 mb-2">Pending Approvals</h1>
        <p className="text-slate-500">
          Review and approve AI-proposed actions before they are executed
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
              <Clock className="w-6 h-6 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Pending Review</p>
              <p className="text-2xl font-bold text-slate-800">{proposals.length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Check className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Approved Today</p>
              <p className="text-2xl font-bold text-slate-800">0</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
              <X className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Rejected Today</p>
              <p className="text-2xl font-bold text-slate-800">0</p>
            </div>
          </div>
        </div>
      </div>

      {/* Proposals List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="font-semibold text-slate-800">AI Action Proposals</h2>
        </div>

        {proposals.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-medium text-slate-700 mb-2">All caught up!</h3>
            <p className="text-slate-500">No pending proposals awaiting your review</p>
          </div>
        ) : (
          <div className="grid gap-4 p-6">
            {proposals.map((proposal) => (
              <div
                key={proposal.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden"
              >
                {/* Card Header */}
                <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 text-slate-600">
                      <Ticket className="w-4 h-4" />
                      <span className="text-sm font-medium">Ticket ID:</span>
                    </div>
                    <span className="text-sm font-mono text-slate-800 bg-white px-2 py-1 rounded border border-slate-200">
                      {proposal.ticket_id}
                    </span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getActionColor(proposal.proposed_action)}`}>
                    {formatActionName(proposal.proposed_action)}
                  </span>
                </div>

                {/* Card Body */}
                <div className="p-6">
                  {/* AI Reasoning Section */}
                  <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                      <Brain className="w-4 h-4 text-indigo-600" />
                      <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
                        AI Reasoning
                      </h4>
                    </div>
                    <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
                      <p className="text-slate-700 text-sm leading-relaxed">
                        {proposal.llm_reasoning}
                      </p>
                    </div>
                  </div>

                  {/* Proposed Action Section */}
                  <div className="mb-6">
                    <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-2">
                      Proposed Action
                    </h4>
                    <p className="text-lg font-medium text-slate-800">
                      {formatActionName(proposal.proposed_action)}
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-3 pt-4 border-t border-slate-100">
                    <button
                      onClick={() => handleApprove(proposal.id)}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-semibold transition-all hover:shadow-lg"
                    >
                      <Check className="w-5 h-5" />
                      Approve
                    </button>
                    <button
                      onClick={() => openRejectModal(proposal.id)}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-semibold transition-all hover:shadow-lg"
                    >
                      <X className="w-5 h-5" />
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reject Modal */}
      {rejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
            {/* Modal Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-800">
                  Why are you rejecting this action?
                </h3>
                <p className="text-sm text-slate-500">
                  Your feedback helps improve the AI
                </p>
              </div>
            </div>

            <form onSubmit={handleReject} className="space-y-4">
              {/* Feedback Text Area */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Rejection Reason
                </label>
                <textarea
                  required
                  value={rejectForm.rejection_reason}
                  onChange={(e) => setRejectForm({ ...rejectForm, rejection_reason: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                  rows={4}
                  placeholder="Explain why this AI proposal is incorrect or inappropriate..."
                />
              </div>

              {/* Reviewer ID (Read-only with hardcoded value) */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Reviewer ID
                </label>
                <input
                  type="text"
                  readOnly
                  value={rejectForm.reviewer_id}
                  className="w-full px-4 py-2 bg-slate-100 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-not-allowed"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Hardcoded for demo purposes
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setRejectModal(null);
                    setRejectForm({ rejection_reason: '', reviewer_id: '' });
                  }}
                  className="flex-1 px-4 py-3 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-semibold transition-colors"
                >
                  Submit Rejection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Toast Provider */}
      <ToastProvider />
    </div>
  );
};

export default PendingProposalsPage;
