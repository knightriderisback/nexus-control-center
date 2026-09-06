import React, { useState } from 'react';
import { 
  Database, 
  Search, 
  Plus, 
  Pin, 
  Trash2, 
  Tag, 
  Sparkles 
} from 'lucide-react';
import type { MemoryNode } from '../types';
import { sound } from '../utils/audio';

interface KnowledgeMatrixProps {
  memories: MemoryNode[];
  onCreateMemory: (title: string, category: string, content: string, tags: string[], pinned: boolean) => Promise<void>;
  onDeleteMemory: (id: string) => Promise<void>;
}

export const KnowledgeMatrix: React.FC<KnowledgeMatrixProps> = ({
  memories,
  onCreateMemory,
  onDeleteMemory
}) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [isCreating, setIsCreating] = useState<boolean>(false);

  // Form state
  const [newTitle, setNewTitle] = useState<string>('');
  const [newCategory, setNewCategory] = useState<string>('Architecture');
  const [newTags, setNewTags] = useState<string>('');
  const [newContent, setNewContent] = useState<string>('');
  const [newPinned, setNewPinned] = useState<boolean>(false);

  const categories = ['ALL', 'Architecture', 'Governance', 'API Contract', 'Directive'];

  const filteredMemories = memories.filter((m) => {
    const matchesCategory = selectedCategory === 'ALL' || m.category === selectedCategory;
    const matchesSearch = 
      m.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.tags.some(t => t.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newContent.trim()) return;

    sound.beep(680, 0.1, 'sine');
    const tagsArray = newTags
      .split(',')
      .map(t => t.trim())
      .filter(Boolean);

    await onCreateMemory(newTitle, newCategory, newContent, tagsArray, newPinned);
    sound.success();
    setNewTitle('');
    setNewTags('');
    setNewContent('');
    setNewPinned(false);
    setIsCreating(false);
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header Bar */}
      <div className="hud-panel p-5 rounded-lg space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cyan-500/20 pb-4">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-bold text-cyan-300 tracking-wider">
              NEURAL CONTEXT & KNOWLEDGE MATRIX
            </span>
          </div>

          <button
            onClick={() => {
              sound.click();
              setIsCreating(prev => !prev);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-500/20 border border-cyan-400 text-cyan-300 hover:bg-cyan-500/30 hover:shadow-[0_0_12px_rgba(0,240,255,0.3)] transition-all text-xs font-bold"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{isCreating ? 'CANCEL' : 'SYNTHESIZE MEMORY'}</span>
          </button>
        </div>

        {/* Search & Category Filter */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search architecture decisions, directives, tags..."
              className="w-full bg-[#070c18] border border-cyan-500/30 rounded pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-400"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  sound.click();
                  setSelectedCategory(cat);
                }}
                className={`px-2.5 py-1.5 rounded text-[11px] border transition-all ${
                  selectedCategory === cat
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_8px_rgba(0,240,255,0.25)]'
                    : 'bg-[#070c18] text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Memory Synthesis Creation Card */}
      {isCreating && (
        <div className="hud-panel p-5 rounded-lg border border-cyan-400/60 shadow-[0_0_15px_rgba(0,240,255,0.2)] space-y-4">
          <div className="flex items-center gap-2 text-cyan-300 text-xs font-bold border-b border-cyan-500/30 pb-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>SYNTHESIZE NEW PERSISTENT MEMORY VECTOR</span>
          </div>

          <form onSubmit={handleCreate} className="space-y-3 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">TITLE</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Distributed Consensus Engine Specification"
                  className="w-full bg-[#070c18] border border-cyan-500/30 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-400 block mb-1">CATEGORY</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="w-full bg-[#070c18] border border-cyan-500/30 rounded px-3 py-2 text-cyan-300 focus:outline-none focus:border-cyan-400"
                >
                  <option value="Architecture">Architecture</option>
                  <option value="Governance">Governance</option>
                  <option value="API Contract">API Contract</option>
                  <option value="Directive">Directive</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 block mb-1">TAGS (COMMA SEPARATED)</label>
              <input
                type="text"
                value={newTags}
                onChange={(e) => setNewTags(e.target.value)}
                placeholder="e.g. cache, latency, websocket, security"
                className="w-full bg-[#070c18] border border-cyan-500/30 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="text-[10px] text-slate-400 block mb-1">CONTENT / SPECIFICATION</label>
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="Technical context, rules, or architectural blueprint..."
                rows={3}
                className="w-full bg-[#070c18] border border-cyan-500/30 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-400"
                required
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <label className="flex items-center gap-2 text-slate-300 text-[11px] cursor-pointer">
                <input
                  type="checkbox"
                  checked={newPinned}
                  onChange={(e) => setNewPinned(e.target.checked)}
                  className="rounded bg-slate-900 border-cyan-500/40 text-cyan-500 focus:ring-0"
                />
                <Pin className="w-3.5 h-3.5 text-amber-400" />
                <span>Pin to Mission Priority</span>
              </label>

              <button
                type="submit"
                className="px-4 py-2 rounded bg-cyan-500/20 border border-cyan-400 text-cyan-300 font-bold hover:bg-cyan-500/30 transition-all text-xs"
              >
                STORE IN VAULT
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Memories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredMemories.map((mem) => (
          <div
            key={mem.id}
            className={`p-4 rounded-lg border flex flex-col justify-between transition-all ${
              mem.pinned
                ? 'bg-[#081022] border-cyan-400/50 shadow-[0_0_12px_rgba(0,240,255,0.15)]'
                : 'bg-[#070b16] border-slate-800 hover:border-cyan-500/30'
            }`}
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-1.5">
                  {mem.pinned && <Pin className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />}
                  <span className="text-xs font-bold text-slate-100 line-clamp-1">
                    {mem.title}
                  </span>
                </div>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-500/30 uppercase flex-shrink-0">
                  {mem.category}
                </span>
              </div>

              <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-4 mb-3">
                {mem.content}
              </p>
            </div>

            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
              <div className="flex flex-wrap gap-1">
                {mem.tags.slice(0, 3).map((t, idx) => (
                  <span key={idx} className="flex items-center gap-0.5 text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded">
                    <Tag className="w-2.5 h-2.5 text-cyan-400" /> {t}
                  </span>
                ))}
              </div>

              <button
                onClick={() => {
                  sound.alert();
                  onDeleteMemory(mem.id);
                }}
                className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                title="Delete memory"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
