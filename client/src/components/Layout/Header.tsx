import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Home, Settings, Brain } from "lucide-react";
import { cn } from "../../utils/cn";

export const Header: React.FC = () => {
  const location = useLocation();

  const navigation = [
    { name: "Dashboard", href: "/", icon: Home },
    { name: "System Info", href: "/settings", icon: Settings },
  ];

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <Brain className="w-8 h-8 text-primary-600" />
            <span className="text-xl font-bold text-gray-900">InstantAI</span>
          </Link>

          {/* Navigation */}
          <nav className="flex space-x-8">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;

              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary-100 text-primary-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Status indicator */}
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-sm text-gray-600">Online</span>
          </div>
        </div>
      </div>
    </header>
  );
};
