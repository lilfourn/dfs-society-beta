-- CreateTable
CREATE TABLE "projections" (
    "id" TEXT NOT NULL,
    "projection_id" TEXT NOT NULL,
    "player_name" TEXT NOT NULL,
    "team" TEXT NOT NULL,
    "position" TEXT NOT NULL,
    "stat_type" TEXT NOT NULL,
    "line_score" DOUBLE PRECISION NOT NULL,
    "average" DOUBLE PRECISION,
    "max_value" DOUBLE PRECISION,
    "game_id" TEXT NOT NULL,
    "start_time" TIMESTAMP(3) NOT NULL,
    "status" TEXT NOT NULL,
    "description" TEXT,
    "image_url" TEXT,
    "odds_type" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "projections_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "projections_projection_id_key" ON "projections"("projection_id");
