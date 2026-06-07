import { NavLink, useNavigate } from "react-router-dom";
import { Icon } from "./Icon";

const NAV = [
  { to: "/search", icon: "search", label: "Search" },
  { to: "/library", icon: "menu_book", label: "Library" },
  { to: "/review", icon: "article", label: "Reviews" },
  { to: "/ingest", icon: "upload_file", label: "Ingest" },
];

function linkClass(active: boolean): string {
  return [
    "flex items-center gap-3 px-4 py-3 cursor-pointer rounded-lg transition-all font-ui-label-md text-ui-label-md",
    active
      ? "bg-primary-container text-on-primary-container font-semibold"
      : "text-on-surface-variant hover:bg-surface-variant",
  ].join(" ");
}

// Desktop docked sidebar (md+) and a mobile bottom bar.
export function Sidebar() {
  const navigate = useNavigate();
  return (
    <>
      <aside className="hidden md:flex flex-col h-screen fixed left-0 top-0 py-6 bg-surface-container-low border-r border-outline-variant w-60 z-40">
        <div className="px-6 mb-8">
          <div className="font-display-lg text-headline-lg-mobile text-primary">Citely</div>
          <div className="font-ui-label-sm text-ui-label-sm text-on-surface-variant mt-1">
            Citation-grounded review
          </div>
        </div>

        <div className="px-4 mb-6">
          <button
            onClick={() => navigate("/review")}
            className="w-full flex justify-center items-center gap-2 bg-primary text-on-primary py-2 px-4 rounded font-ui-label-md text-ui-label-md hover:opacity-90 transition-opacity"
          >
            <Icon name="add" className="text-[18px]" />
            New Review
          </button>
        </div>

        <nav className="flex flex-col gap-1 px-3 flex-1">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => linkClass(isActive)}>
              <Icon name={n.icon} />
              <span>{n.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="flex flex-col gap-1 px-3 mt-auto pt-6 border-t border-outline-variant/30">
          <a
            href="https://arxiv.org"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-variant transition-all font-ui-label-md text-ui-label-md"
          >
            <Icon name="help" />
            <span>About arXiv</span>
          </a>
        </div>
      </aside>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-surface border-t border-outline-variant/30 flex justify-around py-2 z-50">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `flex flex-col items-center px-3 py-1 ${isActive ? "text-primary" : "text-on-surface-variant"}`
            }
          >
            {({ isActive }) => (
              <>
                <Icon name={n.icon} filled={isActive} />
                <span className="font-ui-label-sm text-[10px] mt-0.5">{n.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
